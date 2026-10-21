variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "llmobs-production"
}

variable "environment" {
  description = "Target deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "region" {
  description = "Google Cloud region for resources"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Name of the microservice"
  type        = string
  default     = "alert-engine"
}

variable "min_replicas" {
  description = "Minimum compute replica count"
  type        = number
  default     = 2
}

variable "max_replicas" {
  description = "Maximum compute replica count"
  type        = number
  default     = 8
}
