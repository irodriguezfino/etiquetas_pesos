# Release Process

## Version rule

Edit only `pyproject.toml`:

```toml
[project]
version = "1.0.3"
```

Then run:

```powershell
python tools/versioning.py generate
./scripts/test.ps1
```

## Publish

```powershell
git add .
git commit -m "Release v1.0.3"
git tag -a v1.0.3 -m "Release v1.0.3"
git push origin main
git push origin v1.0.3
```

The `Release` workflow validates that the tag matches `pyproject.toml`, builds from scratch, creates the installer, writes hashes and publishes the GitHub Release.

## First publication

If this repository has no remote yet:

```powershell
git init
git branch -M main
git add .
git commit -m "Initial release-ready version"
git remote add origin https://github.com/OWNER/REPO.git
git push -u origin main
git tag -a v1.0.2 -m "Release v1.0.2"
git push origin v1.0.2
```

Do not force-push and do not overwrite an existing remote.
