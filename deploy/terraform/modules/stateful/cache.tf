resource "aws_elasticache_subnet_group" "redis" {
  name       = "${var.environment}-${var.service_name}-redis-subnet-group"
  subnet_ids = var.subnet_ids

  tags = {
    Name        = "${var.environment}-${var.service_name}-redis-subnet-group"
    Environment = var.environment
  }
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${var.environment}-${var.service_name}-cache"
  engine               = "redis"
  node_type            = "cache.t4g.medium"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = var.security_group_id != "" ? [var.security_group_id] : []

  tags = {
    Environment = var.environment
    Service     = var.service_name
    ManagedBy   = "Terraform"
  }
}

output "cache_endpoint" {
  value = aws_elasticache_cluster.redis.cache_nodes[0].address
}
