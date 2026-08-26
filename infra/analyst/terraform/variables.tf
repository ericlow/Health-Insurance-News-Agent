variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-west-1"
}

variable "account_id" {
  description = "AWS account ID (used to build the self-invocation ARN)"
  type        = string
  default     = "494883819786"
}

variable "function_name" {
  description = "Name of the existing analyst Lambda function"
  type        = string
  default     = "analyst-handler"
}

variable "execution_role_name" {
  description = "Name of the Lambda execution role (not the full ARN)"
  type        = string
  default     = "analyst-handler-role-d7xn9ce7"
}

variable "timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 600
}

variable "memory_size" {
  description = "Lambda memory in MB"
  type        = number
  default     = 128
}

# Secrets — set in terraform.tfvars, never hardcode here.

variable "discord_public_key" {
  description = "Discord application public key for signature verification"
  type        = string
  sensitive   = true
}

variable "discord_application_id" {
  description = "Discord application ID"
  type        = string
  sensitive   = true
}

variable "discord_bot_token" {
  description = "Discord bot token for posting channel messages"
  type        = string
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic API key for Claude"
  type        = string
  sensitive   = true
}

variable "database_url" {
  description = "Neon PostgreSQL connection string"
  type        = string
  sensitive   = true
}

variable "jina_api_key" {
  description = "Jina API key for search_web and fetch_url tools"
  type        = string
  sensitive   = true
}
