output "service_name" {
  description = "The registered microservice name"
  value       = var.service_name
}

output "environment" {
  description = "Current deployment environment"
  value       = var.environment
}

output "security_group_id" {
  description = "Security group attached to the compute workloads"
  value       = module.security.service_security_group_id
}

output "service_role_arn" {
  description = "IAM role ARN assumed by alert-engine service"
  value       = module.security.service_role_arn
}

output "db_endpoint" {
  description = "PostgreSQL / AlloyDB database endpoint"
  value       = module.stateful.db_endpoint
}

output "cache_endpoint" {
  description = "Redis cluster endpoint"
  value       = module.stateful.cache_endpoint
}
