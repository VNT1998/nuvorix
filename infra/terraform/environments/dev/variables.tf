variable "kubeconfig_path" {
  description = "Path to local kubeconfig file"
  type        = string
  default     = "~/.kube/config"
}

variable "namespace" {
  description = "Target Kubernetes namespace"
  type        = string
  default     = "nuvorix-dev"
}

variable "domain" {
  description = "Ingress base domain"
  type        = string
  default     = "dev.nuvorix.local"
}

variable "helm_chart_path" {
  description = "Local path to Helm chart directory"
  type        = string
  default     = "../../../helm/nuvorix"
}
