resource "aws_iam_role" "service_role" {
  name = "${var.environment}-${var.service_name}-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Service     = var.service_name
    ManagedBy   = "Terraform"
  }
}

resource "aws_iam_policy" "alert_engine_policy" {
  name        = "${var.environment}-${var.service_name}-policy"
  description = "Allows access to AWS KMS, Secrets Manager, and telemetry resources"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.service_key.arn
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = "arn:aws:secretsmanager:*:*:${var.environment}/${var.service_name}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "service_attach" {
  role       = aws_iam_role.service_role.name
  policy_arn = aws_iam_policy.alert_engine_policy.arn
}

output "service_role_arn" {
  value = aws_iam_role.service_role.arn
}
