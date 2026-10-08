variable "environment" {
  description = "Environment name used when infrastructure resources are added."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "project_name" {
  description = "Project identifier used for naming future infrastructure resources."
  type        = string
  default     = "masar"
}

