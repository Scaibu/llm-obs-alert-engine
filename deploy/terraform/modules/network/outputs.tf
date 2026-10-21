output "network_id" {
  value = google_compute_network.vpc.id
}

output "network_name" {
  value = google_compute_network.vpc.name
}

output "gke_subnet_id" {
  value = google_compute_subnetwork.subnet_gke.id
}

output "data_subnet_id" {
  value = google_compute_subnetwork.subnet_data.id
}
