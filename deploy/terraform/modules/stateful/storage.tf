resource "aws_s3_bucket" "alert_artifacts" {
  bucket = "${var.environment}-${var.service_name}-artifacts"

  tags = {
    Environment = var.environment
    Service     = var.service_name
    ManagedBy   = "Terraform"
  }
}

resource "aws_s3_bucket_versioning" "artifact_versioning" {
  bucket = aws_s3_bucket.alert_artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifact_crypto" {
  bucket = aws_s3_bucket.alert_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

output "alert_artifacts_bucket_id" {
  value = aws_s3_bucket.alert_artifacts.id
}
