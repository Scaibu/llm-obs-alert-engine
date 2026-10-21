variable "environment" {
  type = string
}

variable "service_name" {
  type = string
}

variable "min_replicas" {
  type    = number
  default = 2
}

variable "max_replicas" {
  type    = number
  default = 8
}
