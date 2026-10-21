terraform {
  backend "s3" {
    bucket         = "llmobs-terraform-state"
    key            = "services/alert-engine/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "llmobs-terraform-locks"
  }
}
