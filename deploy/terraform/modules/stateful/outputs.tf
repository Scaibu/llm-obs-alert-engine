output "secret_arn" {
  value = aws_secretsmanager_secret.db_credentials.arn
}

output "alert_artifacts_bucket_id" {
  value = aws_s3_bucket.alert_artifacts.id
}
