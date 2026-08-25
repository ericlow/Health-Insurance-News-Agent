variable "region" {
  description = "AWS region for the analyst API Gateway"
  type        = string
  default     = "us-west-1"
}

variable "function_name" {
  description = "Name of the existing analyst Lambda function"
  type        = string
  default     = "analyst-handler"
}
