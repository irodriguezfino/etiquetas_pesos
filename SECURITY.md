# Security Policy

## Reporting

Do not open public issues for secrets, credentials, signing problems or update bypasses. Report privately to the project owner.

## Update Security

- Updates are downloaded only from GitHub Releases configured in `update_config.json`.
- Prereleases are ignored unless beta is explicitly enabled.
- The updater requires a SHA-256 hash before applying a downloaded ZIP.
- Files are extracted with path traversal checks.
- User data and local configuration are preserved during updates.

## Sensitive Files

Never commit:

- `.env` files
- GitHub tokens or API keys
- private certificates or signing keys (`.pfx`, `.p12`, `.key`, `.pem`)
- local user data (`config_usuario.json`, `exportaciones/`)
- logs with customer or operational data
