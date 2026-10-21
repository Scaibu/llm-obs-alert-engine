resource "google_service_account" "service_sa" {
  account_id   = "${var.environment}-${var.service_name}-sa"
  display_name = "Service Account for ${var.service_name} on GKE Workload Identity"
}

resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.service_sa.email}"
}

resource "google_project_iam_member" "kms_decrypter" {
  project = var.project_id
  role    = "roles/cloudkms.cryptoKeyDecrypter"
  member  = "serviceAccount:${google_service_account.service_sa.email}"
}

resource "google_service_account_iam_member" "workload_identity_user" {
  service_account_id = google_service_account.service_sa.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[llmobs-${var.environment}/${var.service_name}]"
}

output "service_account_email" {
  value = google_service_account.service_sa.email
}
