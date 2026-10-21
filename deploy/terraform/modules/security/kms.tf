resource "google_kms_key_ring" "keyring" {
  name     = "${var.environment}-${var.service_name}-keyring"
  location = var.region
}

resource "google_kms_crypto_key" "service_key" {
  name            = "${var.environment}-${var.service_name}-key"
  key_ring        = google_kms_key_ring.keyring.id
  rotation_period = "2592000s" # 30 days

  lifecycle {
    prevent_destroy = false
  }
}

output "kms_key_id" {
  value = google_kms_crypto_key.service_key.id
}
