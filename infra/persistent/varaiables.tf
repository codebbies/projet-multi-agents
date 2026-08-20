variable "sql_admin_login" {
  description = "Identifiant administrateur SQL Server"
  type        = string
  sensitive   = true
}

variable "sql_admin_password" {
  description = "Mot de passe administrateur SQL Server"
  type        = string
  sensitive   = true
}