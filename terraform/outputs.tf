output "common_tags" {
  description = "Tags ready to attach to future infrastructure resources."
  value       = local.common_tags
}

output "name_prefix" {
  description = "Naming prefix for future infrastructure resources."
  value       = local.name_prefix
}

