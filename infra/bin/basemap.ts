#!/usr/bin/env node
// Deploys tiles.salishsea.io (SalishSea.io's decision 074) to Orcasound's AWS account:
//   cd infra && pnpm cdk deploy --profile orcasound
// The stack is in us-east-1 because CloudFront only accepts certificates from there, and
// keeping everything in one region lets the stack make and validate its own certificate.
import * as cdk from 'aws-cdk-lib';
import { TilesStack } from '../lib/tiles-stack.ts';

const app = new cdk.App();
new TilesStack(app, 'BasemapTiles', {
  env: { account: '648183724555', region: 'us-east-1' },
  description: 'tiles.salishsea.io: the basemap\'s published builds (salish-sea/basemap)',
});
