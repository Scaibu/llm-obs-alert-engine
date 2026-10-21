output "service_name" {
  description = "The registered microservice name"
  value       = var.service_name
}

output "environment" {
  description = "Current deployment environment"
  value       = var.environment
}

output "network_name" {
  description = "VPC network name"
  value       = module.network.network_name
}

output "service_account_email" {
  description = "GCP Workload Identity Service Account email"
  value       = module.security.service_account_email
}

output "kms_key_id" {
  description = "Cloud KMS Key ID"
  value       = module.security.kms_key_id
}

output "alloydb_ip" {
  description = "AlloyDB Omni cluster internal IP"
  value       = module.stateful.alloydb_ip
}

output "redis_host" {
  description = "Google Cloud Memorystore Redis host"
  value       = module.stateful.redis_host
}

output "alert_artifacts_bucket" {
  description = "Cloud Storage bucket name for alert artifacts"
  value       = module.stateful.alert_artifacts_bucket_name
}
