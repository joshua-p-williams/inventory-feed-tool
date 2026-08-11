# Changelog

All notable project changes will be documented here.

## Unreleased

- Hardened GoDaddy import output with clean Davidsons UPCs, fixed two-decimal money fields, and best-effort Davidsons image URLs.
- Added compact run summaries and full timestamped conversion logs in the output folder.
- Wired the Tkinter desktop app to the new-import workflow with split distributor inputs, output folder selection, basic pricing/image options, and scrollable results.
- Added a UI-independent new-import workflow that runs feed parsing, source aggregation, and GoDaddy CSV export in one pipeline.
- Added a `new-import` CLI command for local conversion verification.
- Added GoDaddy CSV export helpers for new-product import batches.
- Added source aggregation and source-selection helpers for canonical products.
- Added file-based Lipseys and Davidsons CSV feed adapters with sanitized fixture tests.
- Added local SQLite storage for run settings, export runs, external product mappings, source offer snapshots, and source-selection overrides.
- Added canonical inventory model, run configuration policies, pricing helpers, and parsing helpers.
- Added unit tests for model defaults, canonical SKU generation, compliance notes, pricing behavior, and availability parsing.
- Fixed Windows packaging script path handling and failure reporting.
- Added initial Tkinter desktop app shell.
- Added Windows PyInstaller packaging script and workflow.
- Added project-level agent guidance.
- Added initial project skeleton.
- Added feature documentation structure.
- Added minimal Python package with a hello-world CLI.
- Added GitHub Actions CI for unit tests.
