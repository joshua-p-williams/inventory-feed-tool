# Research

## Context

The project needs to support a local utility workflow for converting distributor inventory feeds into website-ready import files. The end user should eventually be able to run a packaged executable with a simple UI.

## Initial Decisions

- Use Python for the ETL core because CSV/XML parsing and validation are straightforward.
- Keep runtime dependencies empty in the skeleton to reduce packaging complexity.
- Use `src/` package layout to avoid accidental imports from the repository root.
- Use standard-library `unittest` for the initial smoke test.
- Use GitHub Actions for basic CI on push and pull request.

## Open Questions

- Which UI toolkit should be used for the packaged desktop app?
- Which packaging approach should be used first: PyInstaller one-folder, PyInstaller one-file, or installer-based distribution?
- Should sample distributor files be committed as sanitized fixtures or kept outside the repository?
