#!/usr/bin/env bash
set -euo pipefail

SERVER_IP="${1:?Usage: $0 <server-ip>}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

scp "$SCRIPT_DIR/Caddyfile" "root@$SERVER_IP:/root/webserver/Caddyfile"

printf '\033[32mCaddyfile copied to server %s\033[0m\n' "$SERVER_IP"
