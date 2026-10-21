module "network" {
  source      = "./modules/network"
  project_id  = var.project_id
  environment = var.environment
  region      = var.region
}

module "security" {
  source       = "./modules/security"
  project_id   = var.project_id
  environment  = var.environment
  service_name = var.service_name
  region       = var.region
}

module "stateful" {
  source         = "./modules/stateful"
  project_id     = var.project_id
  environment    = var.environment
  service_name   = var.service_name
  region         = var.region
  network_id     = module.network.network_id
  data_subnet_id = module.network.data_subnet_id
}

module "stateless" {
  source       = "./modules/stateless"
  environment  = var.environment
  service_name = var.service_name
  min_replicas = var.min_replicas
  max_replicas = var.max_replicas
}
