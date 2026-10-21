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

variable "subnet_ids" {
  type    = list(string)
  default = []
}

variable "security_group_id" {
  type    = string
  default = ""
}

variable "kafka_instance_type" {
  type    = string
  default = "kafka.m5.large"
}

variable "kafka_broker_count" {
  type    = number
  default = 3
}
