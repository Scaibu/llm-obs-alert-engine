resource "google_storage_bucket" "alert_artifacts" {
  name          = "${var.project_id}-${var.environment}-${var.service_name}-artifacts"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}

output "alert_artifacts_bucket_name" {
  value = google_storage_bucket.alert_artifacts.name
}
