# josil-lab

My lab and development environment.

## Terraform

The `terraform/` directory contains the infrastructure configuration for the
lab server in Hetzner Cloud. It uses the official `hetznercloud/hcloud`
provider and provisions:

- an SSH key named `josil-lab-key`, using the public key at `ssh_key_path`;
- an Ubuntu 22.04 server named `josil-lab`;
- public IPv4 and IPv6 networking; and
- a `server_ip` output containing the server's public IPv4 address.

The Hetzner API token is supplied through the sensitive `hcloud_token`
variable. By default, the server is a `cax11` instance in Hetzner's `hel1`
location, and Terraform reads `~/.ssh/id_ed25519.pub` for the SSH public key.
These defaults can be overridden in a local `terraform.tfvars` file or with
Terraform variable flags. Local variable files, state files, and the provider
directory are intentionally ignored by Git so that credentials and deployment
state are not committed.

To review and apply the configuration:

```sh
cd terraform
terraform init
terraform plan
terraform apply
```

Provide `hcloud_token` before planning or applying, for example through a
local, uncommitted `terraform.tfvars` file.

---

> Last updated: 22 October 2026 -- Partly written with AI-tools
