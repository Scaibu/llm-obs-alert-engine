variable "environment" {
  type = string
}

variable "service_name" {
  type = string
}

variable "vpc_id" {
  type    = string
  default = ""
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}
