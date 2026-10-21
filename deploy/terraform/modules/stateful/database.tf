resource "aws_db_subnet_group" "db" {
  name       = "${var.environment}-${var.service_name}-db-subnet-group"
  subnet_ids = var.subnet_ids

  tags = {
    Name        = "${var.environment}-${var.service_name}-db-subnet-group"
    Environment = var.environment
  }
}

resource "aws_db_instance" "database" {
  identifier             = "${var.environment}-${var.service_name}-db"
  allocated_storage      = 50
  max_allocated_storage  = 500
  engine                 = "postgres"
  engine_version         = "15.4"
  instance_class         = var.db_instance_class
  db_name                = "ewma_db"
  username               = "postgres"
  password               = "postgres"
  db_subnet_group_name   = aws_db_subnet_group.db.name
  vpc_security_group_ids = var.security_group_id != "" ? [var.security_group_id] : []
  skip_final_snapshot    = var.environment == "prod" ? false : true
  deletion_protection    = var.environment == "prod" ? true : false

  lifecycle {
    prevent_destroy = false
  }

  tags = {
    Environment = var.environment
    Service     = var.service_name
    ManagedBy   = "Terraform"
  }
}

output "db_endpoint" {
  value = aws_db_instance.database.endpoint
}
