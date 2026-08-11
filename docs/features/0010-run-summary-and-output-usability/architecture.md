# Architecture

## Design Direction

Add UI-independent run summary and log formatting helpers, then have the desktop UI use the compact formatter while writing the full log into the selected output folder.

Proposed module:

```text
src/inventory_feed_tool/
  run_summary.py
```

This keeps formatting and log writing reusable by the CLI, desktop UI, and future run-history features.

## Core Types

Proposed grouped message dataclass:

```python
@dataclass(frozen=True)
class MessageSummary:
    severity: MessageSeverity
    code: str
    field: str | None
    count: int
```

Proposed log result dataclass:

```python
@dataclass(frozen=True)
class WrittenRunLog:
    path: Path
    latest_path: Path | None = None
```

## Core API

Proposed helpers:

```python
def summarize_messages(messages: Iterable[ValidationMessage]) -> tuple[MessageSummary, ...]:
    ...

def format_compact_run_summary(
    result: NewImportWorkflowResult,
    *,
    log_path: Path | None = None,
    max_output_files: int = 10,
) -> str:
    ...

def format_full_run_log(
    result: NewImportWorkflowResult,
    *,
    inputs: NewImportInput,
    configuration: RunConfiguration,
) -> str:
    ...

def write_run_log(
    output_dir: Path,
    text: str,
    *,
    timestamp: datetime | None = None,
    update_latest: bool = True,
) -> WrittenRunLog:
    ...
```

## UI Summary Format

The compact UI summary should include:

```text
Completed with warnings.

Rows seen: 29583
Rows skipped: 0
Offers parsed: 29583
Product groups: 22189
Product groups dropped: 8439
Products exported: 13750
Products skipped: 0

Output files: 138
First files:
C:\...\godaddy-import-001.csv
C:\...\godaddy-import-002.csv
...
Last file:
C:\...\godaddy-import-138.csv

Full log:
C:\...\conversion-log-20260810-143012.txt

Message summary:
WARNING lipseys_missing_upc (UPC): 11
WARNING davidsons_approximate_quantity (Quantity_NC): 123
```

Detailed per-row messages should not appear in the compact UI summary unless the total message count is very small.

## Full Log Format

The full log should include:

1. Heading/status.
2. Source files.
3. Configuration summary:
   - export mode
   - markup percent
   - include image URLs
   - default MAP/availability/compliance policies where useful
4. Counts:
   - rows seen
   - rows skipped
   - offers parsed
   - product groups
   - product groups dropped
   - products exported
   - products skipped
5. Feed parse result summary.
6. Generated output file paths and row counts.
7. Grouped message summary.
8. Detailed messages in original workflow message order.

Use plain text and UTF-8 encoding.

## Log Naming

Use timestamped log names:

```text
conversion-log-YYYYMMDD-HHMMSS.txt
```

Rules:

- Use local time for operator readability.
- Sanitize the timestamp for Windows filenames.
- Do not overwrite an existing timestamped log. If a collision occurs, append a numeric suffix.
- If `update_latest` is true, also write or replace `conversion-log-latest.txt`.

The UI and CLI should display the timestamped log path. The latest-path file is a convenience pointer, not the durable historical record.

## Workflow Boundary

The workflow should remain focused on conversion. It does not need to know about UI-specific compact formatting.

The desktop conversion handler can:

1. call `run_new_import_workflow`
2. build full log text
3. write log into `state.output_dir`
4. format compact UI summary with `log_path`

The CLI `new-import` handler should use the same helpers in this feature:

1. call `run_new_import_workflow`
2. build full log text
3. write log into `args.output_dir`
4. print compact summary with `log_path`
5. preserve current exit-code behavior

## Preflight Validation Behavior

When local UI validation fails before workflow execution:

- show validation messages in the UI
- do not write a log if no valid output folder exists

When workflow executes and returns a result:

- write a full log whenever output folder exists or can be created
- include detailed messages even when the run completed with errors

For CLI preflight validation failures, the workflow may return before an output folder is usable. In that case, print the compact validation result and do not attempt log writing unless the output folder is valid.

## Message Grouping

Group messages by:

1. severity
2. code
3. field

Sort message summaries by:

1. severity priority: error, warning, info
2. descending count
3. code
4. field

## Tests

Coverage should include:

- message grouping by severity/code/field
- compact summary limits output file list
- compact summary includes first/last output file paths
- compact summary includes log path
- full log includes source files
- full log includes configuration summary
- full log includes every detailed message
- write log creates timestamped `conversion-log-*.txt`
- write log can update `conversion-log-latest.txt`
- CLI `new-import` prints compact summary and writes log for completed runs
- UI/app-state tests use compact formatter rather than detailed formatter
