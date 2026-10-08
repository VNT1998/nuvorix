output "dev_console_url" {
  description = "URL for dev environment web console"
  value       = module.nuvorix_cluster.console_ingress_url
}

output "dev_api_url" {
  description = "Internal URL for dev environment API"
  value       = module.nuvorix_cluster.api_service_url
}

output "dev_storage_pvc" {
  description = "Storage PVC created for dev artifacts"
  value       = module.storage.pvc_name
}
