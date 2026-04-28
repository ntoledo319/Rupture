import * as cdk from 'aws-cdk-lib';
import { aws_lambda as lambda } from 'aws-cdk-lib';
import { Construct } from 'constructs';

export class PaymentStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    new lambda.Function(this, 'Payment', {
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset('src/payment'),
    });

    new lambda.Function(this, 'Analytics', {
      runtime: lambda.Runtime.PYTHON_3_10,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset('src/analytics'),
    });

    new lambda.Function(this, 'AlreadyDone', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset('src/done'),
    });
  }
}