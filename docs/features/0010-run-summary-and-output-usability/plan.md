# Plan

1. Add `src/inventory_feed_tool/run_summary.py`.
2. Define `MessageSummary`.
3. Define `WrittenRunLog`.
4. Implement message grouping.
5. Implement compact UI summary formatting.
6. Implement full text log formatting.
7. Implement output-folder log writing.
8. Update desktop conversion flow to write the full log after workflow execution.
9. Update desktop results to show compact summary and log file path.
10. Update CLI `new-import` to write the full log after workflow execution.
11. Update CLI output to use compact summary.
12. Keep existing validation message behavior before workflow execution.
13. Add unit tests for grouping, compact summary, full log, and log writing.
14. Update README and changelog.
15. Update roadmap if implementation changes the next path.

## Proposed Implementation Order

1. `run_summary.py` dataclasses
2. message grouping
3. compact summary formatter
4. full log formatter
5. log writer
6. unit tests for helpers
7. app state formatter replacement
8. GUI conversion handler log writing
9. CLI output/log wiring
10. tests for updated app-state and CLI behavior
11. docs updates

## Locked Decisions

- UI should show grouped message summaries, not every detailed row-level message.
- Full detailed messages must be preserved in timestamped `conversion-log-*.txt`.
- The log file should be written into the selected output folder after each completed workflow run.
- Log writing should not overwrite the only detailed log from a previous run.
- `conversion-log-latest.txt` may be updated as a convenience copy/pointer.
- Plain text and UTF-8 are sufficient.
- Log writing is file-based and does not require SQLite.
- CLI `new-import` should use the same compact summary and log writing behavior.
- Product export limiting is deferred to a later feature.
- GoDaddy export sync remains after this feature.

## Review Points Before Coding

No open review points remain.

## Future Feature Queue

1. `0011-godaddy-export-sync`
2. `0012-update-mode-export`
3. `0013-authenticated-feed-sources`
