variable "environment" {
  description = "Target deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "service_name" {
  description = "Name of the microservice"
  type        = string
  default     = "alert-engine"
}

variable "vpc_cidr" {
  description = "VPC CIDR block for network architecture"
  type        = string
  default     = "10.0.0.0/16"
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

variable "db_instance_class" {
  description = "RDS/AlloyDB database instance class"
  type        = string
  default     = "db.r6g.large"
}
