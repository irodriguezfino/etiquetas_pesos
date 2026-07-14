# Windows Code Signing

## Certificate

For production, use a Windows Authenticode code signing certificate from a trusted CA. EV certificates give better SmartScreen reputation, but standard OV certificates can also sign binaries.

## GitHub Secrets

Create these repository secrets:

- `WINDOWS_CODESIGN_CERTIFICATE_BASE64`: base64 encoded `.pfx`
- `WINDOWS_CODESIGN_CERTIFICATE_PASSWORD`: password for the `.pfx`

Never commit `.pfx`, `.p12`, `.key` or `.pem` files.

## Signing

The release workflow calls:

```powershell
./scripts/sign_windows.ps1 -Path github_release
```

If secrets are absent, signing is skipped and the build still works for development. Unsigned binaries may trigger Windows SmartScreen warnings.

## Verification

The signing script runs:

```powershell
signtool verify /pa /v path\to\file.exe
```
