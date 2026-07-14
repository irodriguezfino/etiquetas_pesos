# Test Plan

Automated:

- `./scripts/test.ps1`
- compile all Python modules
- unit tests for update selection and manifest parsing
- CI build on Windows

Manual before production:

1. Install on a clean Windows user profile.
2. Open the app from the Start Menu and desktop shortcut.
3. Open with no Internet connection; confirm the app still starts.
4. Publish a test release with the same version; confirm no update is offered.
5. Publish a higher test version; confirm detection and release notes.
6. Cancel during download; confirm no files are replaced.
7. Interrupt network during download; confirm error is logged.
8. Replace `.sha256` with an invalid hash in a test release; confirm the ZIP is rejected.
9. Update from the previous installed version.
10. Confirm `config_usuario.json`, `config/plantilla_etiqueta_pesos.json`, `config/backups/` and `exportaciones/` are preserved.
11. Confirm app reopens after update.
12. Uninstall from Windows Apps and confirm application files are removed.
13. Run GitHub Actions CI and Release workflows.
