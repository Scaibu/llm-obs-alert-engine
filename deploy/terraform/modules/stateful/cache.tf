resource "google_redis_instance" "cache" {
  name           = "${var.environment}-${var.service_name}-cache"
  memory_size_gb = 1
  location_id    = "${var.region}-a"
  region         = var.region

  authorized_network = var.network_id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  redis_version     = "REDIS_7_0"
  display_name      = "Alert Engine Redis Ledger"
  auth_enabled      = true
  transit_encryption_mode = "DISABLED"
}

output "redis_host" {
  value = google_redis_instance.cache.host
}

output "redis_port" {
  value = google_redis_instance.cache.port
}
