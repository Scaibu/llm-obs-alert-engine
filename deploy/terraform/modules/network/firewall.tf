resource "google_compute_firewall" "allow_internal_health_metrics" {
  name    = "${var.environment}-allow-health-metrics"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["8001", "9464"]
  }

  source_ranges = ["10.0.0.0/16", "10.48.0.0/14"]
  target_tags   = ["alert-engine"]
}

resource "google_compute_firewall" "allow_data_access" {
  name    = "${var.environment}-allow-data-access"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["5432", "6379", "9092", "9093", "9094"]
  }

  source_tags = ["alert-engine"]
  target_tags = ["data-tier"]
}

resource "google_compute_firewall" "deny_all_external_data" {
  name    = "${var.environment}-deny-external-data"
  network = google_compute_network.vpc.name

  deny {
    protocol = "all"
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["data-tier"]
  priority      = 2000
}
