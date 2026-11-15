# Contact form API

FastAPI accepts JSON `POST /contact` with `name`, `email`, and `message`. Names are limited to 100 characters, email addresses to 254, and messages to 5,000. Names and messages cannot be blank. The application sends from the configured sender to the configured recipient, with the visitor's address as Reply-To. A successful response means the SMTP server accepted the message, not that it was delivered.

All domains, addresses, credentials and paths below are examples: replace them with your own. Never commit real credentials or put them in the image. Use an SMTP provider that supports authenticated STARTTLS on port 587, and an approved sender address (often the same as the login). The application authenticates using `SENDER_EMAIL` as the SMTP username.

## Configuration

| Variable | Meaning |
| --- | --- |
| `SMTP_SERVER` | SMTP hostname, e.g. `smtp.example.com` |
| `SMTP_PORT` | SMTP port; defaults to `587` |
| `SENDER_EMAIL` | Fixed sender and SMTP login, e.g. `sender@example.com` |
| `RECEIVER_EMAIL` | Fixed destination, e.g. `recipient@example.com` |
| `SMTP_PASSWORD_FILE` | Path to a readable UTF-8 file containing the password on one line |
| `CORS_ORIGINS` | Optional comma-separated exact browser origins, e.g. `https://www.example.com,https://example.com`; omit for same-origin use |

Compose sets `SMTP_PASSWORD_FILE` to `/run/secrets/smtp_password`. Configure the other values in a local `.env` next to `compose.yaml` (ignored by Git and Docker), replacing every example:

```dotenv
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SENDER_EMAIL=sender@example.com
RECEIVER_EMAIL=recipient@example.com
CORS_ORIGINS=https://www.example.com
```

CORS controls browser access and is not a spam defense. Only list origins you control. Compose's `.env` is for interpolation; local development requires exporting these variables separately.

## Ubuntu deployment

Install Docker Engine and the Compose plugin. Create the secret on the host outside the repository. The container runs as UID and GID **10001**; ensure that UID can read the file. For a standard rootful Docker installation without user namespace remapping:

```sh
sudo install -d -m 0700 -o root -g root /etc/contact-form
sudo sh -c 'umask 077; cat > /etc/contact-form/smtp_password'
# Enter the SMTP app password, then press Enter and Ctrl-D.
sudo chown 10001:10001 /etc/contact-form/smtp_password
sudo chmod 0400 /etc/contact-form/smtp_password
```

Numeric ownership may correspond to a host account; check `getent passwd 10001` and ensure no untrusted host user can access the file. Docker Compose cannot change UID/GID ownership of file-based secrets: it bind mounts the host file. Rootless Docker or user namespace remapping changes host-to-container UID mapping; adjust ownership for that mapping and verify readability as UID 10001. Host root and Docker administrators can access the secret.

From the project directory, after preparing `.env` and the secret:

```sh
docker compose config
docker compose up -d --build
docker compose logs --tail=50 contact-form
```

Compose binds the application to `127.0.0.1:8000` only. Install Nginx and point DNS for your domain to the server. Allow inbound ports 80 and 443 in the Hetzner firewall and host firewall; do not expose port 8000 publicly. Obtain and renew a certificate with your chosen ACME client (for example Certbot's Nginx integration); configure HTTPS and redirect HTTP to HTTPS. Replace the example domain and certificate paths below. The rate-limit zone belongs in Nginx's `http` block, and the server block serves HTTPS after the certificate exists:

```nginx
limit_req_zone $binary_remote_addr zone=contact_limit:10m rate=5r/m;

server {
    listen 443 ssl;
    server_name api.example.com;
    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;
    client_max_body_size 16k;

    location = /contact {
        limit_req zone=contact_limit burst=3 nodelay;
        limit_req_status 429;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Configure a separate port 80 server to redirect to HTTPS while allowing your ACME challenge as required. Test with `sudo nginx -t` before reloading Nginx. If another proxy sits in front of Nginx, configure trusted real-IP handling so limits apply to clients, not the proxy. Rate limiting reduces excessive requests; monitor abuse and adjust the limit to your traffic.

## Local development and tests

Install Python 3.14 and [uv](https://docs.astral.sh/uv/), then run `uv sync`. Create a local password file outside the repository, restrict access, and export the variables above with `SMTP_PASSWORD_FILE` pointing to that file. Run `uv run uvicorn contact_form.main:app --reload --host 127.0.0.1 --port 8000`. Requests to `/contact` attempt real SMTP delivery, so use mocked tests for development when delivery is unwanted:

```sh
uv run python -m unittest discover -s tests -v
```

## Password rotation and troubleshooting

Create the replacement credential with your SMTP provider, update the host file securely while preserving the ownership and mode above, and recreate the container with `docker compose up -d --force-recreate`. The password is read at startup; recreating also ensures a replaced file is remounted. Verify service startup and revoke the old credential once the replacement works. Never paste credentials into commands, logs, issues, or Git.

If startup fails, inspect `docker compose logs contact-form` for the named missing or invalid setting. Check the secret path, host ownership, file mode, UID mapping, and that the file contains a nonempty single-line UTF-8 password. For delivery failures, check provider credentials, sender authorization, DNS, outbound access to port 587, and the provider's TLS certificate. The service logs a generic failure without message contents or credentials. Check Nginx logs and origin settings for browser or 429 errors; CORS origins must match scheme, host, and port exactly. Do not include secrets or message contents in support requests.
