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
- Compact run summaries and full output-folder conversion logs.
- Import-output hardening for clean UPCs, fixed money formatting, and Davidsons image URL coverage.

The file-based new-import workflow is usable from both CLI and desktop UI. The next major gap is GoDaddy export sync, which is needed before reliable update-mode exports can be produced.

## Recently Completed

### 0011-import-output-quality-hardening

Fixed issues discovered by analyzing a full generated GoDaddy new-import output folder.

Completed scope:

- Blank invalid UPC placeholders such as `##` before GoDaddy export while preserving fallback SKUs.
- Normalize hash-wrapped Davidsons UPC values to clean digit strings.
- Format GoDaddy money fields with fixed two-decimal output.
- Add conservative Davidsons image URL construction from public item-number-based image hosting patterns.
- Add regression tests for invalid UPC, money formatting, and Davidsons image URL behavior.
- Re-analyze generated output to confirm no `UPC=##`, no duplicate SKUs, consistent headers, fixed money formatting, and improved Davidsons image coverage.

### 0010-run-summary-and-output-usability

Improved the usability of large conversion runs before adding update-mode workflows.

Completed scope:

- Summarize validation messages by severity, code, field, and count in the UI and CLI.
- Keep generated output file paths visible without flooding the results area.
- Write a full timestamped text conversion log into the selected output folder for every completed run.
- Include run counts, source files, configuration summary, generated CSV files, warnings, and errors in the log.
- Preserve detailed per-row messages in the output-folder log even when the UI and CLI show grouped summaries.
- Update `conversion-log-latest.txt` as a convenience copy.
- Defer max-products/export limiting to a later feature.

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

### 0012-godaddy-export-sync

Import GoDaddy product exports and sync GoDaddy `PRODUCT ID` mappings into SQLite.

Expected scope:

- Parse GoDaddy product export CSV files.
- Match rows back to canonical SKUs and UPCs.
- Store `target_system = "godaddy"` external product mappings.
- Report ambiguous or missing mappings.
- Prepare reliable update-mode coverage checks.

This feature should remain after the new-import workflow because it serves update mode, not the first usable import flow.

### 0013-update-mode-export

Enable GoDaddy update CSV generation once product ID mappings are available.

Expected scope:

- Use storage-backed GoDaddy product ID lookup.
- Require mapping coverage or fail affected rows clearly.
- Populate `PRODUCT ID` for update exports.
- Preserve new-import behavior separately.

### 0014-authenticated-feed-sources

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
