# Local Project Storage

## Purpose

Add local SQLite storage for run settings, export history, source offer snapshots, product mappings, and future user overrides.

The storage layer should make repeat runs safer without requiring a server, cloud account, or external database.

## Scope

- Define where the local database file should live.
- Define SQLite schema and migration/versioning approach.
- Store last-used run configuration defaults.
- Store export run metadata.
- Store external product mappings between canonical identity and target-system product IDs.
- Store source offer snapshots enough to support audit/history and future source selection.
- Store source-selection overrides for future aggregation/export features.
- Add storage APIs with unit tests.

## Out of Scope

- Parsing distributor feeds.
- Aggregating source offers.
- Writing target CSV exports.
- Importing target product exports.
- Building the desktop UI for managing mappings/settings.
- Syncing data to any cloud service.

Those will be separate features.

## Success Criteria

- The app can create/open a local SQLite database with the expected schema.
- Storage initialization is idempotent.
- The app can save and load last-used run configuration.
- The app can create export run records.
- The app can upsert and retrieve external product mappings by target system, canonical SKU, and UPC.
- The app can store source offer snapshots for an export run.
- The app can store source-selection overrides.
- The storage layer uses only Python standard-library dependencies.
- Unit tests cover database initialization and the core repository operations.
