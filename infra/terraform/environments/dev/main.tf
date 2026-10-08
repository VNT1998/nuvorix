terraform {
  required_version = ">= 1.5.0"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.23.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.11.0"
    }
  }
}

provider "kubernetes" {
  config_path = var.kubeconfig_path
}

provider "helm" {
  kubernetes {
    config_path = var.kubeconfig_path
  }
}

module "storage" {
  source       = "../../modules/storage"
  namespace    = var.namespace
  prefix       = "nuvorix-dev"
  environment  = "dev"
  storage_size = "20Gi"
}

module "nuvorix_cluster" {
  source                = "../../modules/nuvorix_cluster"
  namespace             = var.namespace
  release_name          = "nuvorix-dev"
  environment           = "dev"
  domain                = var.domain
  helm_chart_repository = var.helm_chart_path
  api_replicas          = 2
  web_replicas          = 1

  depends_on = [module.storage]
}
