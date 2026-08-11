# Run Summary And Output Usability

## Purpose

Improve the usability of production-scale conversion runs.

Real sample files can produce many GoDaddy CSV batches and many repeated warnings. The desktop UI should stay readable, while the selected output folder should contain a durable full text log with all details needed to review or troubleshoot the run later.

## Scope

- Add compact run summary formatting for UI display.
- Summarize validation messages by severity, code, and count in the UI.
- Keep generated output file paths visible without flooding the UI results area.
- Write a full text conversion log to the selected output folder for each completed workflow run.
- Include source files, run counts, configuration summary, output files, grouped message counts, and detailed messages in the log.
- Preserve detailed per-row warnings/errors in the output-folder log even when the UI shows grouped summaries.
- Display the log file path in the UI after conversion.
- Use durable log filenames so a later run does not destroy the only detailed log from an earlier run.
- Apply the same compact summary and output-folder log behavior to CLI `new-import` runs.
- Add tests for message grouping, UI summary formatting, and full log content.

## Out Of Scope

- GoDaddy product export import.
- GoDaddy update-mode export.
- SQLite-backed run history.
- Opening the output folder automatically.
- Product review queue.
- Editing source-selection overrides.
- Authenticated feed retrieval.
- Replacing CSV batch export behavior.
- Max-products/export limiting for small test imports.

Those remain separate features.

## Success Criteria

- Large runs show a compact UI summary instead of hundreds of repeated warning lines.
- UI summary includes counts, output file count, first/last output file paths, log file path, and grouped message counts.
- A full text log is written to the selected output folder after every completed conversion run.
- Log writing does not overwrite the only detailed log from a previous run in the same folder.
- The full log includes all detailed validation messages from the workflow result.
- The full log includes the generated GoDaddy CSV file list.
- The full log includes the selected source file paths and visible run options.
- Partial-success runs still write a full log and show generated file paths.
- CLI `new-import` output uses the compact summary and writes the same full text log.
- Preflight validation failures that do not have an output folder do not attempt to write a log.
- Tests cover UI summary formatting and full log formatting without launching Tkinter.
