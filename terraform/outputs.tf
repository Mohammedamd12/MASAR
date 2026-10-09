output "common_tags" {
  description = "Tags ready to attach to future infrastructure resources."
  value       = local.common_tags
}

output "bigquery_datasets" {
  description = "BigQuery datasets managed by this module."
  value = {
    raw     = google_bigquery_dataset.raw.dataset_id
    staging = google_bigquery_dataset.staging.dataset_id
    marts   = google_bigquery_dataset.marts.dataset_id
  }
}

output "gcp_project_id" {
  description = "Google Cloud project used by Masar."
  value       = var.gcp_project_id
}

output "name_prefix" {
  description = "Naming prefix for future infrastructure resources."
  value       = local.name_prefix
}

output "pipeline_service_account" {
  description = "Service account used by the Masar data pipeline."
  value       = google_service_account.pipeline.email
}

output "raw_bucket_name" {
  description = "Cloud Storage bucket for raw source data."
  value       = google_storage_bucket.raw_data.name
}

