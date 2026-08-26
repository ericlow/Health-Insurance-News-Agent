# Manages analyst-handler Lambda configuration and IAM self-invocation policy.
#
# The Lambda function and its execution role were created outside Terraform.
# This config imports the function to manage its env vars and runtime config,
# and attaches an inline IAM policy for engine-mode self-invocation.
# Code deployments remain via CLI (see infra/analyst/README.md).

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

# Look up the existing execution role by name.
data "aws_iam_role" "analyst" {
  name = var.execution_role_name
}

# Managed resource for the existing Lambda function.
# Import before first apply:
#   terraform import aws_lambda_function.analyst analyst-handler
#
# lifecycle ignores code changes so CLI deploys don't conflict with Terraform.
resource "aws_lambda_function" "analyst" {
  function_name = var.function_name
  role          = data.aws_iam_role.analyst.arn
  runtime       = "python3.12"
  handler       = "agent.analyst.interactions.handler"
  timeout       = var.timeout
  memory_size   = var.memory_size

  # Placeholder keeps the resource block valid before import.
  # Terraform never uploads this — ignore_changes prevents it.
  filename = "/dev/null"

  environment {
    variables = {
      DISCORD_PUBLIC_KEY     = var.discord_public_key
      DISCORD_APPLICATION_ID = var.discord_application_id
      DISCORD_BOT_TOKEN      = var.discord_bot_token
      ANTHROPIC_API_KEY      = var.anthropic_api_key
      DATABASE_URL           = var.database_url
      JINA_API_KEY           = var.jina_api_key
    }
  }

  lifecycle {
    # Code is deployed via CLI (see README). Terraform only manages config.
    ignore_changes = [filename, source_code_hash, layers]
  }
}

# Inline IAM policy: allows the Lambda to invoke itself for engine mode.
resource "aws_iam_role_policy" "self_invoke" {
  name = "analyst-handler-self-invoke"
  role = data.aws_iam_role.analyst.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = "arn:aws:lambda:${var.region}:${var.account_id}:function:${var.function_name}"
    }]
  })
}
