# Google Cloud Managed Service for Apache Kafka / Compute Engine Kafka Cluster
resource "google_compute_instance_template" "kafka_template" {
  name_prefix  = "${var.environment}-kafka-template-"
  machine_type = "e2-standard-2"
  region       = var.region

  disk {
    source_image = "debian-cloud/debian-11"
    auto_delete  = true
    boot         = true
    disk_size_gb = 50
  }

  network_interface {
    network    = var.network_id
    subnetwork = var.data_subnet_id
  }

  tags = ["data-tier", "kafka-broker"]

  lifecycle {
    create_before_destroy = true
  }
}

resource "google_compute_region_instance_group_manager" "kafka_cluster" {
  name               = "${var.environment}-kafka-cluster"
  base_instance_name = "kafka-broker"
  region             = var.region
  target_size        = 3

  version {
    instance_template = google_compute_instance_template.kafka_template.id
  }
}

output "kafka_cluster_name" {
  value = google_compute_region_instance_group_manager.kafka_cluster.name
}
