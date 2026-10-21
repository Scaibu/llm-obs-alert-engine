resource "google_compute_global_address" "private_ip_alloc" {
  name          = "${var.environment}-private-ip-alloc"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = var.network_id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = var.network_id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_alloc.name]
}

resource "google_alloydb_cluster" "default" {
  cluster_id = "${var.environment}-${var.service_name}-alloydb"
  location   = var.region
  network_config {
    network = var.network_id
  }

  initial_user {
    user     = "postgres"
    password = "alloysecretpassword2024"
  }

  depends_on = [google_service_networking_connection.private_vpc_connection]
}

resource "google_alloydb_instance" "primary" {
  cluster       = google_alloydb_cluster.default.name
  instance_id   = "${var.environment}-${var.service_name}-primary"
  instance_type = "PRIMARY"

  machine_config {
    cpu_count = 2
  }
}

output "alloydb_ip" {
  value = google_alloydb_instance.primary.ip_address
}
