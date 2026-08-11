# Feature Roadmap

This roadmap captures the current project state and the expected feature order. It should be updated whenever new implementation work changes the next best path.

## Current Position

The project now has the core ETL building blocks:

- Shared inventory model and run configuration policies.
- SQLite storage for settings, export runs, product mappings, source snapshots, and source-selection overrides.
- File-based Lipseys and Davidsons feed adapters.
- Source aggregation and selected-offer logic.
- GoDaddy CSV exporter for new-product import batches.
- New-import workflow orchestration for file-based feeds to GoDaddy CSV batches.
- Desktop conversion flow and packaging workflow.

The important remaining gap is update-mode support. The file-based new-import workflow is usable from both CLI and desktop UI, but GoDaddy `PRODUCT ID` mappings still need to be imported before update exports can be generated safely.

## Recently Completed

### 0009-desktop-ui-conversion-flow

Connected the desktop shell to the new-import workflow.

Completed scope:

- File pickers for Lipseys, Davidsons inventory feed, and Davidsons quantity feed.
- Output folder selection for generated CSV batches.
- Basic pricing and image options.
- Clear status, warnings, and generated-file summary.
- Guardrails for missing files and invalid input combinations.

### 0008-new-import-workflow

Wired the existing ETL pieces into one end-to-end new-import pipeline.

Completed scope:

- Accept one or more distributor source inputs.
- Support running Lipseys alone, Davidsons alone, or both together.
- Support Davidsons' separate quantity file as an optional companion input.
- Apply `RunConfiguration`.
- Parse source feeds into `SourceOffer` records.
- Aggregate source offers into selected `CanonicalProduct` records.
- Export GoDaddy new-import CSV batches.
- Return a run summary with counts, output files, warnings, and errors.
- Keep the pipeline UI-independent so CLI and desktop app can share it.
- Add a minimal CLI command for local verification.

## Recommended Next Path

### 0010-godaddy-export-sync

Import GoDaddy product exports and sync GoDaddy `PRODUCT ID` mappings into SQLite.

Expected scope:

- Parse GoDaddy product export CSV files.
- Match rows back to canonical SKUs and UPCs.
- Store `target_system = "godaddy"` external product mappings.
- Report ambiguous or missing mappings.
- Prepare reliable update-mode coverage checks.

This feature should remain after the new-import workflow because it serves update mode, not the first usable import flow.

### 0011-update-mode-export

Enable GoDaddy update CSV generation once product ID mappings are available.

Expected scope:

- Use storage-backed GoDaddy product ID lookup.
- Require mapping coverage or fail affected rows clearly.
- Populate `PRODUCT ID` for update exports.
- Preserve new-import behavior separately.

### 0012-authenticated-feed-sources

Evaluate authenticated distributor feed retrieval after the file-based workflow is working.

Expected scope:

- Research available dealer-authorized API, FTP, or download options.
- Keep credentials out of source control.
- Prefer optional retrieval plugins/services around the existing file adapter contracts.

## Deferred Ideas

- Category mapping for storefront taxonomy if the target import schema supports it.
- Product review queue for allocated, unknown, restricted, or conflict-heavy items.
- Richer manual override management in the desktop UI.
- Additional target exporters beyond GoDaddy.
- Additional distributor adapters.

## Roadmap Notes

- Keep raw distributor inventory files out of the repository.
- Keep downloaded reference material outside the repository unless it is a summarized reference note under `docs/references`.
- Keep the repo generic and avoid hardcoded business, customer, or operator names.
- Continue using one feature folder per implementation feature under `docs/features`.
