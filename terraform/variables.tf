variable "environment" {
  description = "Environment name used when infrastructure resources are added."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "gcp_project_id" {
  description = "Google Cloud project that hosts the Masar data platform."
  type        = string
  default     = "saudi-industrial-mobility"
}

variable "gcp_region" {
  description = "Google Cloud region for regional resources."
  type        = string
  default     = "me-central1"
}

variable "project_name" {
  description = "Project identifier used for naming future infrastructure resources."
  type        = string
  default     = "masar"
}

