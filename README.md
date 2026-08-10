# Inventory Feed Tool

Inventory Feed Tool is a local ETL utility for converting distributor inventory feeds into normalized product data and exporting website-ready import files.

The first export target is the GoDaddy product import CSV format. The first supported feed sources are planned to be Davidsons and Lipseys.

## Goals

- Normalize distributor catalog and inventory feeds into a shared internal product model.
- Export products to website import formats, starting with GoDaddy CSV.
- Keep the utility easy to package as a Windows executable with a simple UI.
- Keep source adapters isolated so new distributors can be added without rewriting the ETL engine.
- Produce validation messages so bad source rows do not crash the whole conversion.

## Current Foundation

The ETL core currently includes the shared model pieces that feed adapters and exporters will use:

- `RunConfiguration` and policy objects for pricing, availability, source selection, image handling, compliance behavior, and export mode.
- `SourceOffer` for one distributor's listing of a product.
- `CanonicalProduct` for one sellable product grouped from one or more distributor offers.
- Configurable MAP-aware pricing helpers.
- Reusable parsing helpers for money, booleans, optional text, and availability tokens.
- Local SQLite storage for settings, export runs, external product mappings, source offer snapshots, and source-selection overrides.
- File-based Lipseys and Davidsons CSV adapters that produce normalized `SourceOffer` records and validation messages.
- Source aggregation and selection helpers that group offers into exportable `CanonicalProduct` records.
- GoDaddy CSV export helpers for new-product import batches.

## Project Structure

```text
inventory-feed-tool/
  .github/workflows/       GitHub Actions automation
  docs/features/           Feature-by-feature SDLC notes
  src/inventory_feed_tool/ Python package source
  tests/                   Automated tests
  CHANGELOG.md             Human-readable project history
  pyproject.toml           Python package metadata
```

## Feature Workflow

Work is organized under `docs/features/`. Each feature gets its own folder with:

- `feature.md`: user-facing purpose and scope
- `research.md`: findings, unknowns, sample data notes, and decisions
- `architecture.md`: implementation shape and design tradeoffs
- `plan.md`: intended implementation path
- `tasks.md`: checklist of concrete work items

This keeps assisted coding work reviewable and gives future changes a place to preserve context.

## Development

Create a local virtual environment and install the package:

```bash
python -m venv .venv
.venv/bin/python -m pip install -e .
```

Run the hello-world CLI from the repository root:

```bash
.venv/bin/python -m inventory_feed_tool
```

Run the desktop app shell:

```bash
.venv/bin/inventory-feed-tool-gui
```

On Linux, this requires the system Tkinter package. On Ubuntu-based systems that is usually `python3-tk`. Windows Python distributions typically include Tkinter.

Run tests:

```bash
.venv/bin/python -m unittest discover -s tests
```

## Packaging Direction

The application is designed so the ETL core, CLI, and desktop UI can share the same conversion services.

The first packaging target is a PyInstaller one-folder Windows build. From Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
.\scripts\build_windows.ps1 -Clean
```

The expected build output is:

```text
dist/InventoryFeedTool/InventoryFeedTool.exe
```

GitHub Actions also includes a manual `Windows Package` workflow that uploads the packaged app as an artifact.
