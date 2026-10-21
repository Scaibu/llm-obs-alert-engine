variable "environment" {
  type = string
}

variable "service_name" {
  type = string
}

variable "db_instance_class" {
  type    = string
  default = "db.r6g.large"
}
