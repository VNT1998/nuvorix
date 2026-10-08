terraform {
  required_version = ">= 1.5.0"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.31.0"
    }
  }
}

resource "kubernetes_persistent_volume_claim_v1" "artifact_storage" {
  metadata {
    name      = "${var.prefix}-artifact-store"
    namespace = var.namespace
    labels = {
      app         = "nuvorix"
      environment = var.environment
    }
  }
  spec {
    access_modes = ["ReadWriteMany"]
    resources {
      requests = {
        storage = var.storage_size
      }
    }
  }
}
