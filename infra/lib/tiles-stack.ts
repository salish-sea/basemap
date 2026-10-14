// tiles.salishsea.io: a private bucket of published builds behind CloudFront, in us-west-2,
// and its certificate, in us-east-1.
//
// Each build is uploaded once under its own path (`/2026-10-13/…`) and never changed, so
// a page that names a build always gets the same map, and every file can be cached for a
// year. Maps fetch from other sites, so every response allows any origin, and PMTiles
// archives are read in pieces with HTTP range requests, which S3 and CloudFront serve as
// they are.

import * as cdk from 'aws-cdk-lib';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as route53Targets from 'aws-cdk-lib/aws-route53-targets';
import * as s3 from 'aws-cdk-lib/aws-s3';
import type { Construct } from 'constructs';

const DOMAIN = 'tiles.salishsea.io';

// The salishsea.io zone lives in this account; SalishSea.io's own stack uses it too.
function salishseaZone(scope: Construct): route53.IHostedZone {
  return route53.HostedZone.fromHostedZoneAttributes(scope, 'Zone', {
    hostedZoneId: 'Z0267557TOKCHC5IUMVH',
    zoneName: 'salishsea.io',
  });
}

/** The certificate for tiles.salishsea.io, in us-east-1, the only region CloudFront takes it from. */
export class CertificateStack extends cdk.Stack {
  readonly certificate: acm.ICertificate;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);
    this.certificate = new acm.Certificate(this, 'Certificate', {
      domainName: DOMAIN,
      validation: acm.CertificateValidation.fromDns(salishseaZone(this)),
    });
  }
}

export interface TilesStackProps extends cdk.StackProps {
  certificate: acm.ICertificate;
}

export class TilesStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: TilesStackProps) {
    super(scope, id, props);
    const zone = salishseaZone(this);

    const bucket = new s3.Bucket(this, 'Builds', {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      // Published builds are what pages link to; deleting the stack must not delete them.
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      // A backstop: a file overwritten by mistake can still be recovered by an admin.
      versioned: true,
      // A publish killed partway leaves uploaded parts that would otherwise be billed for ever.
      lifecycleRules: [{ abortIncompleteMultipartUploadAfter: cdk.Duration.days(1) }],
      // Answers CORS preflights, which CloudFront passes through to S3 (below). Browsers
      // send none for pmtiles' single-range requests today, but other clients may.
      cors: [{
        allowedOrigins: ['*'],
        allowedMethods: [s3.HttpMethods.GET, s3.HttpMethods.HEAD],
        allowedHeaders: ['*'],
        exposedHeaders: ['ETag', 'Content-Length', 'Content-Range', 'Accept-Ranges'],
        maxAge: 86400,
      }],
    });

    // Any site may draw the map. This sets the CORS headers on every response, whatever
    // S3 sent; pmtiles reads the ETag to notice an archive changing under it.
    const cors = new cloudfront.ResponseHeadersPolicy(this, 'Cors', {
      responseHeadersPolicyName: 'basemap-tiles-cors',
      comment: `${DOMAIN}: any origin may fetch the map`,
      corsBehavior: {
        accessControlAllowOrigins: ['*'],
        accessControlAllowMethods: ['GET', 'HEAD', 'OPTIONS'],
        accessControlAllowHeaders: ['*'],
        accessControlExposeHeaders: ['ETag', 'Content-Length', 'Content-Range', 'Accept-Ranges'],
        accessControlAllowCredentials: false,
        accessControlMaxAge: cdk.Duration.days(1),
        originOverride: true,
      },
    });

    const distribution = new cloudfront.Distribution(this, 'Distribution', {
      comment: `${DOMAIN}: the basemap's published builds (decision 074)`,
      domainNames: [DOMAIN],
      certificate: props.certificate,
      priceClass: cloudfront.PriceClass.PRICE_CLASS_100,
      httpVersion: cloudfront.HttpVersion.HTTP2_AND_3,
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(bucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
        // Preflights go to S3 with their Origin and Access-Control-Request-* headers;
        // they aren't cached here, since the cache key leaves those headers out.
        cachedMethods: cloudfront.CachedMethods.CACHE_GET_HEAD,
        originRequestPolicy: cloudfront.OriginRequestPolicy.CORS_S3_ORIGIN,
        // Files are uploaded with a year's Cache-Control (scripts/publish.sh), which this
        // policy honours. The archives are already compressed inside; only the style and
        // the viewer's files gain from compression.
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
        compress: true,
        responseHeadersPolicy: cors,
      },
    });

    const target = route53.RecordTarget.fromAlias(new route53Targets.CloudFrontTarget(distribution));
    new route53.ARecord(this, 'ARecord', { zone, recordName: 'tiles', target });
    new route53.AaaaRecord(this, 'AaaaRecord', { zone, recordName: 'tiles', target });

    // The user scripts/publish.sh runs as on a build machine: it can find the bucket and
    // add files to it, and nothing else. It can't delete or overwrite a file, since a
    // published version never changes. Its access key is made by hand
    // (`aws iam create-access-key --user-name basemap-publisher`), so the secret never
    // passes through CloudFormation.
    const publisher = new iam.User(this, 'Publisher', { userName: 'basemap-publisher' });
    publisher.addToPolicy(new iam.PolicyStatement({
      actions: ['cloudformation:DescribeStacks'],
      resources: [this.stackId],
    }));
    // Listing lets a check for a missing file answer "not found" rather than "denied".
    publisher.addToPolicy(new iam.PolicyStatement({
      actions: ['s3:ListBucket'],
      resources: [bucket.bucketArn],
    }));
    publisher.addToPolicy(new iam.PolicyStatement({
      actions: ['s3:GetObject', 's3:AbortMultipartUpload'],
      resources: [bucket.arnForObjects('*')],
    }));
    // Uploads only of files that don't exist yet: the request must say `If-None-Match: *`,
    // which `aws s3 cp --no-overwrite` sends. The parts of a multipart upload can't carry
    // the header, so they're allowed; the upload's completion is a creation and must.
    publisher.addToPolicy(new iam.PolicyStatement({
      actions: ['s3:PutObject'],
      resources: [bucket.arnForObjects('*')],
      conditions: { Null: { 's3:if-none-match': 'false' } },
    }));
    publisher.addToPolicy(new iam.PolicyStatement({
      actions: ['s3:PutObject'],
      resources: [bucket.arnForObjects('*')],
      conditions: { Bool: { 's3:ObjectCreationOperation': 'false' } },
    }));

    new cdk.CfnOutput(this, 'BucketName', {
      value: bucket.bucketName,
      description: 'Where scripts/publish.sh uploads each build',
    });
    new cdk.CfnOutput(this, 'DistributionId', { value: distribution.distributionId });
  }
}
