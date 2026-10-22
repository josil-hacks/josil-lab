# GitHub Actions

This directory contains the repository's GitHub Actions configuration.

## Deployment workflow

[`workflows/deploy.yaml`](workflows/deploy.yaml) runs whenever a commit is
pushed to the `main` branch. Its job is named `build-and-deploy` and performs
the following work in order:

1. Checks out the repository with full git history.
2. Compares the previous and current commit in the push to determine whether
   any file ending in `.py` changed. For the first push to a branch, it checks
   the files in the pushed commit instead.
3. If Python changed, installs the Python quality tools, runs `ruff check .`
   for linting, and runs `bandit --recursive . --exclude .git` to scan Python
   code for common security vulnerabilities.
4. Logs in to GitHub Container Registry, builds the Docker image, and pushes
   both `latest` and the commit-SHA tag.
5. Connects to the VPS over SSH and pulls/restarts the Docker Compose service.

The Python setup, lint, and vulnerability-scan steps are skipped when a push
does not include a `.py` file. Image building and deployment still run for
every push to `main`.

## Required secrets

The deployment step requires these repository secrets:

- `VPS_HOST` — hostname or IP address of the deployment server.
- `VPS_SSH_KEY` — private SSH key used to connect as `root`.

`GITHUB_TOKEN` is provided automatically by GitHub Actions and is used to
authenticate to GitHub Container Registry.
