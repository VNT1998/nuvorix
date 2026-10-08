output "pvc_name" {
  description = "Persistent volume claim name"
  value       = kubernetes_persistent_volume_claim_v1.artifact_storage.metadata[0].name
}
