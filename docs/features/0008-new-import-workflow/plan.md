# Plan

1. Add `src/inventory_feed_tool/workflows/`.
2. Add `workflows/new_import.py`.
3. Define `NewImportInput`.
4. Define `NewImportWorkflowResult`.
5. Implement preflight validation helpers.
6. Implement source parsing orchestration.
7. Combine source offers and call aggregation.
8. Call GoDaddy CSV exporter with output directory and filename prefix.
9. Preserve messages from all pipeline stages.
10. Add unit tests with temporary CSV inputs and output folders.
11. Update README and changelog.
12. Update roadmap if implementation changes the next feature order.

## Proposed Implementation Order

1. package structure
2. input/result dataclasses
3. result summary properties or count calculations
4. preflight validation
5. parser orchestration
6. aggregation call
7. export call
8. tests for validation failures
9. tests for successful one-source runs
10. tests for combined-source runs
11. README and changelog updates

## Locked Decisions

- `0008` creates an end-to-end new-import workflow before GoDaddy product export sync.
- Workflow input uses an output directory, not a single output CSV path.
- Lipseys-only runs are valid.
- Davidsons inventory-only runs are valid.
- Davidsons inventory plus quantity runs are valid.
- Lipseys plus Davidsons runs are valid.
- Davidsons quantity-only runs are invalid.
- The workflow applies one `RunConfiguration` to parsing, aggregation, and export.
- The workflow accepts optional `SourceSelectionOverride` values from the caller.
- The workflow does not open SQLite directly.
- The workflow does not implement update mode.
- The workflow returns structured result objects, not only strings.
- The workflow preserves validation messages from adapters, aggregation, and exporter.
- Desktop UI wiring remains out of scope unless implementation is small enough to add safely.

## Review Points Before Coding

Resolved:

- Include a minimal CLI command for local verification.
- Keep the exporter default `godaddy-import` prefix, with a CLI/workflow override option.

## Future Feature Queue

1. `0009-desktop-ui-conversion-flow`
2. `0010-godaddy-export-sync`
3. `0011-update-mode-export`
4. `0012-authenticated-feed-sources`
