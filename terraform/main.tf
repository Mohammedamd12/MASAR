provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  common_tags = {
    environment = var.environment
    managed_by  = "terraform"
    project     = var.project_name
  }
}

resource "google_storage_bucket" "raw_data" {
  name                        = "${var.gcp_project_id}-raw-data"
  location                    = var.gcp_region
  force_destroy               = false
  public_access_prevention    = "enforced"
  uniform_bucket_level_access = true

  labels = local.common_tags

  versioning {
    enabled = true
  }
}

resource "google_bigquery_dataset" "raw" {
  dataset_id                 = "masar_raw"
  friendly_name              = "Masar Raw"
  description                = "Raw traffic, weather, and government event data."
  location                   = var.gcp_region
  delete_contents_on_destroy = false
  labels                     = local.common_tags
}

resource "google_bigquery_dataset" "staging" {
  dataset_id                 = "masar_staging"
  friendly_name              = "Masar Staging"
  description                = "Cleaned and standardized Masar data."
  location                   = var.gcp_region
  delete_contents_on_destroy = false
  labels                     = local.common_tags
}

resource "google_bigquery_dataset" "marts" {
  dataset_id                 = "masar_marts"
  friendly_name              = "Masar Marts"
  description                = "Analytics-ready tables consumed by Streamlit."
  location                   = var.gcp_region
  delete_contents_on_destroy = false
  labels                     = local.common_tags
}

resource "google_service_account" "pipeline" {
  account_id   = "masar-pipeline"
  display_name = "Masar data pipeline"
  description  = "Runtime identity for Airflow, dbt, and Streamlit."
}

resource "google_project_iam_member" "pipeline_roles" {
  for_each = toset([
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser",
    "roles/storage.objectAdmin",
  ])

  project = var.gcp_project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.pipeline.email}"
}

