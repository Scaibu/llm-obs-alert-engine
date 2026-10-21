resource "aws_msk_cluster" "kafka" {
  cluster_name           = "${var.environment}-llmobs-kafka"
  kafka_version          = "3.5.1"
  number_of_broker_nodes = var.kafka_broker_count

  broker_node_group_info {
    instance_type   = var.kafka_instance_type
    client_subnets  = var.subnet_ids
    security_groups = [var.security_group_id]
    storage_info {
      ebs_storage_info {
        volume_size = 100
      }
    }
  }

  encryption_info {
    encryption_in_transit {
      client_broker = "TLS_PLAINTEXT"
      in_cluster    = true
    }
  }

  tags = {
    Environment = var.environment
    Service     = "shared-messaging"
    ManagedBy   = "Terraform"
  }
}

output "kafka_bootstrap_brokers" {
  value = aws_msk_cluster.kafka.bootstrap_brokers
}

output "kafka_arn" {
  value = aws_msk_cluster.kafka.arn
}
