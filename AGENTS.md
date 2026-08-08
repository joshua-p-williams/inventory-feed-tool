# Agent Instructions

This repository contains Inventory Feed Tool, a Python ETL utility for converting distributor inventory feeds into website-ready product import files.

## Project Priorities

- Keep the ETL core separate from user interfaces. CLI and desktop UI code should call shared services instead of duplicating conversion logic.
- Keep packaging as a first-class requirement. Prefer dependencies that are compatible with PyInstaller or a similar Windows executable packaging flow.
- Keep distributor-specific logic isolated behind feed adapters.
- Normalize source feeds into a canonical internal product model before exporting to GoDaddy or other website formats.
- Treat validation and reporting as product behavior. Bad source rows should produce actionable warnings when possible, not crash the entire conversion.

## Documentation Workflow

Feature work should be documented under `docs/features/<feature-id>/`.

Each feature folder should usually include:

- `feature.md`
- `research.md`
- `architecture.md`
- `plan.md`
- `tasks.md`

Keep feature docs current as implementation decisions change.

## Data Handling

- Do not commit real distributor inventory feeds unless they are explicitly approved for redistribution.
- Prefer sanitized fixtures for tests.
- Avoid committing business-private pricing, account, or distributor credential data.
- Generated exports should go under `outputs/`, which is ignored by git.

## Engineering Guidelines

- Use the existing `src/` package layout.
- Prefer standard-library modules until a dependency meaningfully improves the implementation.
- Add focused tests with each behavioral change.
- Keep GoDaddy export formatting driven by the known import template columns.
- Update `CHANGELOG.md` for notable project changes.

## Verification

Use the local virtual environment workflow from `README.md`.

Common checks:

```bash
.venv/bin/python -m inventory_feed_tool
.venv/bin/inventory-feed-tool --version
.venv/bin/python -m unittest discover -s tests
```
