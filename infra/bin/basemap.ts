#!/usr/bin/env node
// Deploys tiles.salishsea.io (SalishSea.io's decision 074) to Orcasound's AWS account:
//   cd infra && pnpm cdk deploy --all --profile orcasound
// The bucket and distribution are in us-west-2, beside SalishSea.io's own stack. CloudFront
// only accepts certificates from us-east-1, so the certificate has a stack of its own
// there. The distribution reads its ARN from that stack's outputs (a weak reference, set
// in cdk.json), so a replaced certificate is picked up on the next `deploy --all`; a
// strong one would keep the old ARN in SSM.
import * as cdk from 'aws-cdk-lib';
import { CertificateStack, TilesStack } from '../lib/tiles-stack.ts';

const ACCOUNT = '648183724555';
const app = new cdk.App();
const certificate = new CertificateStack(app, 'BasemapCertificate', {
  env: { account: ACCOUNT, region: 'us-east-1' },
  description: 'tiles.salishsea.io: the certificate CloudFront needs, which must be in us-east-1',
});
new TilesStack(app, 'BasemapTiles', {
  env: { account: ACCOUNT, region: 'us-west-2' },
  certificate: certificate.certificate,
  description: 'tiles.salishsea.io: the basemap\'s published builds (salish-sea/basemap)',
});
