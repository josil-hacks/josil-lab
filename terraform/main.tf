terraform {
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.45"
    }
  }
}

provider "hcloud" {
  token = var.hcloud_token
}

resource "hcloud_ssh_key" "josil-lab" {
  name       = "josil-lab-key"
  public_key = file(var.ssh_key_path)
}

resource "hcloud_server" "web" {
  name        = "josil-lab"
  image       = "ubuntu-22.04"
  server_type = var.server_type
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.josil-lab.id]

  public_net {
    ipv4_enabled = true
    ipv6_enabled = true
  }
}

output "server_ip" {
  value = hcloud_server.web.ipv4_address
}