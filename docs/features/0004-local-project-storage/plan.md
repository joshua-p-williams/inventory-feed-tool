# Plan

1. Add `storage.py` using Python standard-library `sqlite3`.
2. Implement app-data database path discovery.
3. Implement connection setup and schema initialization.
4. Implement JSON serialization helpers for `RunConfiguration`.
5. Add small dataclasses for stored rows where useful, such as `ExternalProductMapping` and `SourceOverride`.
6. Implement settings, export run, external product mapping, source offer snapshot, and source override operations.
7. Add focused unit tests with temporary SQLite files.
8. Update README and changelog.

## Proposed Implementation Order

1. `default_database_path`
2. `connect_database`
3. `initialize_database`
4. `RunConfiguration` JSON serialization helpers
5. `LocalStore`
6. setting save/load
7. run configuration save/load
8. export run creation
9. external product mapping upsert/find
10. source offer snapshot insert
11. source override upsert/find
12. tests
13. README and changelog updates

## Locked Decisions

- Use SQLite through Python's standard-library `sqlite3`.
- Store the database under the user's app-data location by default, not inside the executable or repository.
- Use `PRAGMA user_version` for migrations.
- Initial schema version is `1`.
- Store money values as text to preserve decimal precision.
- Store run configuration as JSON.
- Store target-system product IDs only when learned externally; never generate them. GoDaddy `PRODUCT ID` is the first concrete case.
- Do not store raw distributor feed files or credentials.
- Keep source offer snapshots for audit/history in the MVP.
- Scope source-selection overrides by target system and canonical SKU.
- Keep storage APIs generic and free of hardcoded business/operator names.

## Future Feature Queue Impact

This feature supports:

- `0005-source-aggregation-and-selection`
- `0006-godaddy-csv-exporter`
- `0007-godaddy-export-sync`
- `0008-update-mode-export`
