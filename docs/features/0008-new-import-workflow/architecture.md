# Architecture

## Design Direction

Add a UI-independent workflow module that composes existing ETL components.

Proposed module layout:

```text
src/inventory_feed_tool/
  workflows/
    __init__.py
    new_import.py
```

The workflow should own run orchestration. It should not duplicate feed parsing, source selection, or GoDaddy row mapping logic.

## Core API

Proposed input dataclass:

```python
@dataclass(frozen=True)
class NewImportInput:
    lipseys_csv: Path | None = None
    davidsons_inventory_csv: Path | None = None
    davidsons_quantity_csv: Path | None = None
    output_dir: Path | None = None
```

Proposed result dataclass:

```python
@dataclass(frozen=True)
class NewImportWorkflowResult:
    feed_results: tuple[FeedParseResult, ...]
    aggregation_result: AggregationResult | None
    export_result: GoDaddyExportResult | None
    messages: tuple[ValidationMessage, ...]
    source_rows_seen: int
    source_rows_skipped: int
    source_offers_parsed: int
    product_groups: int
    product_groups_dropped: int
    products_exported: int
    products_skipped: int
```

Proposed public function:

```python
def run_new_import_workflow(
    inputs: NewImportInput,
    configuration: RunConfiguration | None = None,
    *,
    overrides: Iterable[SourceSelectionOverride] = (),
    filename_prefix: str = "godaddy-import",
) -> NewImportWorkflowResult:
    ...
```

## Validation Flow

Before parsing:

1. Require at least one primary source file:
   - `lipseys_csv`
   - `davidsons_inventory_csv`
2. Reject `davidsons_quantity_csv` without `davidsons_inventory_csv`.
3. Require `output_dir`.
4. Validate every provided source path exists and is a file.
5. Validate `output_dir` is not an existing regular file.
6. Reject unsupported export modes early when possible.

If preflight validation returns errors, the workflow should return a result with no feed, aggregation, or export work performed.

## Processing Flow

When preflight validation succeeds:

1. Normalize `configuration` to `RunConfiguration()` when omitted.
2. Parse Lipseys if `lipseys_csv` is provided.
3. Parse Davidsons if `davidsons_inventory_csv` is provided, passing `davidsons_quantity_csv` when provided.
4. Combine all parsed source offers.
5. Aggregate offers with `aggregate_source_offers`.
6. Export `aggregation_result.products` with `export_godaddy_csv`.
7. Combine parser, aggregation, and exporter messages into the workflow result.

## Message Handling

The workflow should preserve messages rather than reducing them to plain text.

Message order:

1. Preflight validation messages.
2. Feed adapter messages in source processing order.
3. Aggregation run-level messages.
4. Exporter messages.

Product-level warnings and conflicts remain attached to `CanonicalProduct` instances inside the aggregation result. The workflow does not need to flatten them in this feature.

## Source Processing Order

Use deterministic source order:

1. Lipseys
2. Davidsons

This makes test expectations stable. It does not define source preference; selected-offer choice still belongs to aggregation and `RunConfiguration.source_selection`.

## Export Target

This feature should call the existing GoDaddy exporter directly.

That is intentionally target-specific because GoDaddy is the only implemented exporter. The workflow name should still describe the business operation, not the lower-level exporter, so a later target option can be added without renaming every concept.

## Storage Boundary

The workflow should not open SQLite directly in this feature.

Callers may:

- load `RunConfiguration` from `LocalStore`
- load storage `SourceOverride` rows and translate them into `SourceSelectionOverride`
- call `run_new_import_workflow`

A later feature can add an application service that combines `LocalStore` with this workflow and records run history.

## Error Behavior

Use validation messages for expected user-correctable problems:

- missing source files
- invalid input combinations
- output directory conflict
- unsupported export mode

Raise exceptions only for programming errors or unexpected filesystem failures that cannot be represented cleanly.

## Tests

Tests should use temporary directories and small CSV fixtures created by the test code.

Coverage should include:

- Lipseys-only happy path.
- Davidsons-only happy path.
- Davidsons with quantity file.
- Both distributors in one run.
- Quantity-only validation failure.
- Missing file validation failure.
- Output directory path points to existing file.
- Update mode rejected.
- Adapter, aggregation, and exporter messages are included.
- Multiple output batch files can be reported.
