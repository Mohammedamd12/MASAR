locals {
  name_prefix = "${var.project_name}-${var.environment}"
  common_tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
    Project     = var.project_name
  }
}

# Cloud resources will be added after choosing the target provider and region.
# Keeping this root module provider-neutral makes the first `terraform plan` safe.

