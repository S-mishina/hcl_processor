module "api_monitors" {
  source = "../../../monitor"

  monitors = local.api_monitors

  for_each = toset(["error_rate", "latency"])

  monitor_name = each.key
  environment  = var.environment
  tags         = var.tags
}

variable "environment" {
  type        = string
  description = "Environment name (dev, stg, prd)"
}

variable "tags" {
  type        = list(string)
  description = "Tags to apply to all monitors"
  default     = []
}
