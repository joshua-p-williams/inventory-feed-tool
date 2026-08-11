# Research

## Real Run Observation

A Windows packaged run against available sample files completed successfully with warnings.

Observed counts:

```text
Rows seen: 29583
Rows skipped: 0
Offers parsed: 29583
Product groups: 22189
Product groups dropped: 8439
Products exported: 13750
Products skipped: 0
Output files: 138
```

The output is internally consistent:

- `13,750` exported products at GoDaddy's 100-product batch size produces `138` CSV files.
- `8,439` dropped groups are expected under conservative availability rules when products have no exportable selected offer.
- `0` exporter skips means aggregation handed the exporter valid selected products.

The run also produced many repeated warnings such as:

- missing UPC with source-SKU fallback
- approximate Davidsons quantities
- missing Davidsons quantity-file matches
- invalid UPC with source-SKU fallback

## Usability Finding

The conversion works at production scale, but current result formatting is too verbose for the UI.

Current UI behavior:

- Shows every output file path.
- Shows every detailed warning/error message.
- Preserves details, but the results area becomes noisy for large runs.

Desired behavior:

- UI should quickly answer "Did this run work, what files did it create, and what types of warnings occurred?"
- Full output-folder log should answer "What exactly happened on every row/message?"

## Prior Feature Decisions

From `0007-godaddy-csv-exporter`:

- GoDaddy import batches are capped at 100 products.
- Exporter writes deterministic batch names like `godaddy-import-001.csv`.

From `0008-new-import-workflow`:

- Workflow returns structured counts, output files, and `ValidationMessage` objects.
- Workflow does not write storage or logs directly yet.

From `0009-desktop-ui-conversion-flow`:

- Desktop app formats workflow results in `app_state.py`.
- Result formatting is UI-independent and testable.
- Generated file paths must remain visible even when row-level errors occur.
- Output folder is selected by the operator before conversion.

## Log File Decision

Use timestamped log names:

```text
conversion-log-YYYYMMDD-HHMMSS.txt
```

Reasons:

- Plain text is easy to open on Windows without extra tooling.
- The name describes that it contains full details, not only a short summary.
- Timestamped names keep a later run from destroying the only detailed log from an earlier run in the same output folder.

Optionally also update:

```text
conversion-log-latest.txt
```

This gives the operator a stable "latest run" filename while preserving timestamped historical logs. If this adds complexity, prioritize timestamped durable logs first.

## UI Summary Decision

UI should show:

- completion heading
- primary counts
- output file count
- first few output files
- last output file when many files were generated
- log file path
- grouped message counts by severity and code

Detailed row-level messages should move to the log.

## CLI Parity

The CLI currently prints every workflow message. The same production-scale usability problem applies there.

Decision for this feature:

- CLI `new-import` should write the full output-folder log.
- CLI `new-import` should print the compact summary to stdout.
- CLI exit code behavior should stay the same: nonzero when the workflow result contains errors.

## Optional Export Limit

An optional max-products/export limit was considered for test imports.

Decision for this feature:

- Defer product export limiting to a later feature.
- Prioritize summary/logging first because it is needed for every real run.

## Open Questions

No blocking questions remain.
