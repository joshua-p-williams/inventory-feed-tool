# New Import Workflow

## Purpose

Create the first end-to-end conversion workflow for new-product imports.

This feature wires the existing file adapters, source aggregation, and GoDaddy CSV exporter into a single UI-independent service that can be called by the CLI, desktop app, tests, or future automation.

## Scope

- Add an orchestration module for new-import runs.
- Accept Lipseys CSV input, Davidsons inventory CSV input, or both.
- Accept the Davidsons quantity CSV as an optional companion to the Davidsons inventory CSV.
- Reject a Davidsons quantity CSV without a Davidsons inventory CSV.
- Apply one `RunConfiguration` consistently across feed parsing, aggregation, and export.
- Load source-selection overrides from optional caller-provided data.
- Parse distributor feeds into `SourceOffer` records.
- Aggregate source offers into selected `CanonicalProduct` records.
- Export GoDaddy new-import CSV batches.
- Return a run result with parsed counts, aggregation counts, exported files, warnings, and errors.
- Use an output directory, not a single output CSV path, because the GoDaddy exporter can create multiple 100-product batch files.
- Add focused tests with temporary CSV files and generated output folders.

## Out Of Scope

- Full desktop UI wiring.
- Rich pricing/settings UI.
- GoDaddy product export import.
- GoDaddy update-mode export.
- Authenticated distributor API, FTP, or website download automation.
- Manual review screens.
- Editing or persisting source-selection overrides.
- Product category mapping beyond existing model fields.
- Importing raw inventory files into SQLite.

Those remain separate features.

## Success Criteria

- A caller can run Lipseys-only conversion to GoDaddy new-import CSV files.
- A caller can run Davidsons-only conversion with or without the quantity CSV.
- A caller can run Lipseys and Davidsons together in one aggregation/export run.
- The workflow rejects missing source files with clear validation messages.
- The workflow rejects Davidsons quantity-only input with a clear validation message.
- The workflow rejects update mode because the GoDaddy exporter does not support it yet.
- All parser, aggregation, and exporter messages are preserved in the final result.
- The result reports source rows seen, rows skipped, source offers parsed, product groups, products exported, products skipped, and output files.
- No output files are written when validation fails before parsing.
- Tests do not depend on real distributor feed files.
