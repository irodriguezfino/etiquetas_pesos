# Contributing

## Local setup

```powershell
./scripts/install_deps.ps1
./scripts/test.ps1
```

## Rules

- Do not commit generated folders such as `build/`, `dist/` or `github_release/`.
- Do not commit credentials, `.env` files, private certificates or signing keys.
- Keep `pyproject.toml` as the only manually edited version source.
- Run `./scripts/secret_scan.ps1` before publishing.
