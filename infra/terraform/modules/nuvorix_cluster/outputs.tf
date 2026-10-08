output "namespace" {
  description = "The namespace where Nuvorix is installed"
  value       = kubernetes_namespace_v1.nuvorix.metadata[0].name
}

output "api_service_url" {
  description = "Internal service URL for the API control plane"
  value       = "http://${var.release_name}-api.${kubernetes_namespace_v1.nuvorix.metadata[0].name}.svc.cluster.local:8000"
}

output "console_ingress_url" {
  description = "Public URL for Nuvorix Web Console"
  value       = "https://console.${var.domain}"
}
