variable "hcloud_token" {
  description = "Hetzner Cloud API token"
  type        = string
  sensitive   = true
}

variable "ssh_key_path" {
  description = "Path to the SSH public key file"
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}

variable "server_type" {
  description = "Type of the server to create"
  type        = string
  default     = "cax11"
}

variable "location" {
  description = "Location of the server"
  type        = string
  default     = "hel1"
}