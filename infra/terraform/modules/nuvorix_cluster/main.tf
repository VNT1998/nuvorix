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

resource "kubernetes_namespace" "nuvorix" {
  metadata {
    name = var.namespace
    labels = {
      name        = var.namespace
      environment = var.environment
      managed-by  = "terraform"
    }
  }
}

resource "helm_release" "nuvorix" {
  name       = var.release_name
  repository = var.helm_chart_repository
  chart      = var.helm_chart_name
  version    = var.helm_chart_version
  namespace  = kubernetes_namespace.nuvorix.metadata[0].name

  set {
    name  = "global.environment"
    value = var.environment
  }

  set {
    name  = "global.domain"
    value = var.domain
  }

  set {
    name  = "api.replicaCount"
    value = var.api_replicas
  }

  set {
    name  = "web.replicaCount"
    value = var.web_replicas
  }
}
