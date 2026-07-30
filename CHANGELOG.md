# Changelog

All notable changes to Etiquetado Pesos are documented here.

## [1.0.9] - 2026-07-30

- The updater now waits for both the application and launcher processes, then closes residual application instances before replacing executables.
- Access denied (`WinError 5`) is retried as a temporary file lock, alongside Windows sharing violations.

## [1.0.8] - 2026-07-30

- Article options with identical names and percentages now include their article code, so each cloned article selects only its own weight ranges.

## [1.0.7] - 2026-07-30

- The updater now waits for the previous launcher to exit before replacing installed files.
- File replacement is atomic and automatically retries Windows sharing violations for up to 45 seconds.
- Failed updates identify the locked file in the dialog, status file and updater log.

## [1.0.6] - 2026-07-30

- The article selector groups repeated products and shows their available percentages.
- Labels preserve the percentage in the original CSV position while keeping the selected weight range in its own section.
- Weight bounds such as `<13` and `+19` are excluded from the article name and remain selectable as ranges.
- Improved certificate handling for update discovery and downloads.

## [1.0.5] - 2026-07-14

- Article selector now displays only the article name while retaining code-based range lookup and search.

## [1.0.4] - 2026-07-14

- Improved help tooltips: delayed hover activation, no focus activation, immediate dismissal on interaction, and screen-bound placement.

## [1.0.3] - 2026-07-14

- Preserved the previous update distribution history.
- Added legacy manifest publishing so existing 1.0.2 installations can update to GitHub Releases.

## [1.0.2] - 2026-07-14

- Prepared reproducible packaging with PyInstaller and Inno Setup.
- Added GitHub Releases based update discovery.
- Added SHA-256 verified update manifest generation.
- Added CI and release workflows.
- Added version single source of truth in `pyproject.toml`.
