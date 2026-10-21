resource "google_secret_manager_secret" "db_credentials" {
  secret_id = "${var.environment}-${var.service_name}-database"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_credentials_val" {
  secret = google_secret_manager_secret.db_credentials.id

  secret_data = jsonencode({
    username = "postgres"
    password = "alloysecretpassword2024"
    database = "ewma_db"
  })
}

output "secret_id" {
  value = google_secret_manager_secret.db_credentials.id
}
