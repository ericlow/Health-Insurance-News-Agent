# API Gateway (HTTP API) in front of the existing analyst-handler Lambda.
#
# The Lambda function, its role, and code were created outside Terraform
# (console + CLI). This config only manages the public HTTP entrance, because
# Lambda Function URLs are blocked by the account's public-access setting.
# The function is referenced via a data source, not created here.

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

data "aws_lambda_function" "analyst" {
  function_name = var.function_name
}

resource "aws_apigatewayv2_api" "analyst" {
  name          = "analyst-interactions"
  protocol_type = "HTTP"
  description   = "Discord interactions endpoint for the Analyst agent"
}

resource "aws_apigatewayv2_integration" "analyst" {
  api_id                 = aws_apigatewayv2_api.analyst.id
  integration_type       = "AWS_PROXY"
  integration_uri        = data.aws_lambda_function.analyst.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "analyst" {
  api_id    = aws_apigatewayv2_api.analyst.id
  route_key = "POST /"
  target    = "integrations/${aws_apigatewayv2_integration.analyst.id}"
}

resource "aws_apigatewayv2_stage" "analyst" {
  api_id      = aws_apigatewayv2_api.analyst.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = data.aws_lambda_function.analyst.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.analyst.execution_arn}/*/*"
}

output "interactions_endpoint_url" {
  description = "Paste this into the Discord Developer Portal > Interactions Endpoint URL"
  value       = aws_apigatewayv2_stage.analyst.invoke_url
}
