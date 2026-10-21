resource "aws_security_group" "service" {
  name        = "${var.environment}-${var.service_name}-sg"
  description = "Security group for ${var.service_name} compute workloads"
  vpc_id      = var.vpc_id != "" ? var.vpc_id : null

  ingress {
    description = "Health and metrics ingress within VPC"
    from_port   = 8001
    to_port     = 9464
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Environment = var.environment
    Service     = var.service_name
    ManagedBy   = "Terraform"
  }
}

resource "aws_security_group" "data" {
  name        = "${var.environment}-${var.service_name}-data-sg"
  description = "Firewall security group for PostgreSQL/AlloyDB, Redis, and Kafka brokers"
  vpc_id      = var.vpc_id != "" ? var.vpc_id : null

  ingress {
    description     = "PostgreSQL access from service SG"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.service.id]
  }

  ingress {
    description     = "Redis access from service SG"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.service.id]
  }

  ingress {
    description     = "Kafka plaintext/TLS broker access from service SG"
    from_port       = 9092
    to_port         = 9098
    protocol        = "tcp"
    security_groups = [aws_security_group.service.id]
  }

  egress {
    description = "Allow outbound data communication within VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Environment = var.environment
    Service     = "shared-data-plane"
    ManagedBy   = "Terraform"
  }
}

output "service_security_group_id" {
  value = aws_security_group.service.id
}

output "data_security_group_id" {
  value = aws_security_group.data.id
}
