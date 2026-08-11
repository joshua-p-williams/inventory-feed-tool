# Research

## Prior Feature Decisions

From `0005-distributor-feed-adapters`:

- Lipseys and Davidsons adapters are file-based.
- Lipseys can run independently.
- Davidsons inventory can run independently.
- Davidsons quantity CSV is optional but only meaningful with a Davidsons inventory CSV.
- Adapters produce `FeedParseResult` objects and do not aggregate or export.
- Adapters use `RunConfiguration` for pricing and availability behavior.

From `0006-source-aggregation-and-selection`:

- Aggregation receives `SourceOffer` records and returns `CanonicalProduct` records.
- Aggregation drops all-non-exportable product groups from returned products.
- Aggregation returns run-level warnings when groups are dropped.
- Source-selection overrides are passed as plain data and should be translated by orchestration if loaded from storage.
- The aggregation module should not open SQLite connections.

From `0007-godaddy-csv-exporter`:

- GoDaddy new-import mode is supported.
- New imports leave `PRODUCT ID` blank.
- Update mode is intentionally rejected until GoDaddy product export sync exists.
- GoDaddy bulk CSV upload is limited to 100 products, so the exporter writes batch files.
- Exporter input is `CanonicalProduct`, not raw distributor offers.
- Exporter does not parse files, aggregate offers, or query SQLite.

## Current Code Shape

The current code already exposes the pieces needed by an orchestration layer:

```text
feeds.parse_lipseys_csv(path, configuration)
feeds.parse_davidsons_inventory_csv(inventory_path, configuration, quantity_path=None)
aggregate_source_offers(offers, configuration, overrides=())
export_godaddy_csv(products, output_dir, configuration)
```

The desktop app and CLI still use placeholder behavior. This feature should create the service they can call later.

## Workflow Implications

The workflow should treat each distributor input independently:

- Lipseys only is valid.
- Davidsons inventory only is valid.
- Davidsons inventory plus quantity is valid.
- Lipseys plus Davidsons inventory is valid.
- Lipseys plus Davidsons inventory plus Davidsons quantity is valid.

The workflow should reject:

- no source files
- Davidsons quantity file without Davidsons inventory file
- source paths that do not exist
- output directory paths that cannot be prepared

## Output Folder Decision

The original desktop shell used a single "GoDaddy output CSV" path. The exporter can produce more than one file because GoDaddy import batches are capped at 100 products.

For the workflow, use an output directory and deterministic exporter file names. A later UI feature should update the desktop shell from single output CSV selection to output folder selection.

## Storage Decision

`0008` should not require SQLite to run.

Reasons:

- The first new-import workflow is useful without existing product mappings.
- Tests are simpler and faster when the workflow can run without persistent state.
- Update-mode mapping behavior belongs to later GoDaddy sync/export features.

Optional storage integration can be added in this feature only if it stays small:

- caller may provide already-loaded source-selection overrides
- caller may provide a run configuration loaded from storage

Persisting run history and source offer snapshots can be added later without changing the workflow's public model.

## Open Questions

No blocking questions remain.

Review point before coding:

- Confirm whether `0008` should include a minimal CLI command for local verification, or only the orchestration service and tests.
