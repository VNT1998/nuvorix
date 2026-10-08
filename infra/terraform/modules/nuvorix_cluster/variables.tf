variable "namespace" {
  description = "Kubernetes namespace for Nuvorix resources"
  type        = string
  default     = "nuvorix"
}

variable "release_name" {
  description = "Helm release name"
  type        = string
  default     = "nuvorix"
}

variable "environment" {
  description = "Deployment environment name"
  type        = string
  default     = "development"
}

variable "domain" {
  description = "Base domain name for ingress routing"
  type        = string
  default     = "nuvorix.local"
}

variable "helm_chart_repository" {
  description = "Helm chart repository or path"
  type        = string
  default     = "../../helm/nuvorix"
}

variable "helm_chart_name" {
  description = "Name of the Helm chart"
  type        = string
  default     = "nuvorix"
}

variable "helm_chart_version" {
  description = "Version of the Helm chart"
  type        = string
  default     = "0.1.0"
}

variable "api_replicas" {
  description = "Number of API control plane replicas"
  type        = number
  default     = 2
}

variable "web_replicas" {
  description = "Number of Web frontend replicas"
  type        = number
  default     = 2
}
