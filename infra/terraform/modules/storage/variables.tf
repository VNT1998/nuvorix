variable "namespace" {
  description = "Target Kubernetes namespace"
  type        = string
  default     = "nuvorix"
}

variable "prefix" {
  description = "Prefix identifier for storage resources"
  type        = string
  default     = "nuvorix"
}

variable "environment" {
  description = "Environment identifier"
  type        = string
  default     = "development"
}

variable "storage_size" {
  description = "Size requested for persistent volume storage"
  type        = string
  default     = "50Gi"
}
