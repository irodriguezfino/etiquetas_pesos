# Changelog

All notable changes to Etiquetado Pesos are documented here.

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
