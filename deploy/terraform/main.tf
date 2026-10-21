module "network" {
  source      = "./modules/network"
  environment = var.environment
  vpc_cidr    = var.vpc_cidr
}

module "security" {
  source       = "./modules/security"
  environment  = var.environment
  service_name = var.service_name
  vpc_id       = module.network.vpc_id
  vpc_cidr     = module.network.vpc_cidr
}

module "stateful" {
  source            = "./modules/stateful"
  environment       = var.environment
  service_name      = var.service_name
  db_instance_class = var.db_instance_class
  subnet_ids        = module.network.data_subnet_ids
  security_group_id = module.security.data_security_group_id
}

module "stateless" {
  source       = "./modules/stateless"
  environment  = var.environment
  service_name = var.service_name
  min_replicas = var.min_replicas
  max_replicas = var.max_replicas
}
