resource "aws_lambda_function" "payment" {
  function_name = "payment-webhook"
  role          = aws_iam_role.lambda.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.9"
  filename      = "payment.zip"
}

resource "aws_lambda_function" "analytics" {
  function_name = "analytics-daily"
  role          = aws_iam_role.lambda.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.10"
  filename      = "analytics.zip"
}

resource "aws_lambda_function" "done" {
  function_name = "already-migrated"
  role          = aws_iam_role.lambda.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  filename      = "done.zip"
}