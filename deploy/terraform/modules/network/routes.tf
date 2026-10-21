# VPC routes - custom routes can be added here
resource "google_compute_route" "default_internet" {
  name             = "${var.environment}-default-internet-route"
  dest_range       = "0.0.0.0/0"
  network          = google_compute_network.vpc.name
  next_hop_gateway = "default-internet-gateway"
  priority         = 1000
}
