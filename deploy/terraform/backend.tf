terraform {
  backend "gcs" {
    bucket = "llmobs-terraform-state"
    prefix = "services/alert-engine"
  }
}
