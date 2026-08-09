# Research

## Inputs From Previous Feature

Feature `0003-canonical-inventory-model` established the model and future storage needs:

- `RunConfiguration` controls export mode, pricing, availability, source selection, image handling, and compliance behavior.
- GoDaddy owns `PRODUCT ID`; the tool must not invent those IDs.
- New imports leave `PRODUCT ID` blank.
- Update imports require external product ID mappings learned from a target-system export. GoDaddy is the first supported target system.
- Product identity should prefer UPC-based canonical SKUs.
- Source offers should be preserved so conflicts and source decisions remain auditable.

## SQLite Fit

SQLite is a good fit for this utility:

- Included in Python's standard library through `sqlite3`.
- Works in a packaged desktop executable without installing a separate database.
- Stores structured state locally and transparently.
- Supports migrations through a small schema version table or `PRAGMA user_version`.
- Handles this project's expected scale comfortably.

## App Data Location

The database should not live inside the installed executable folder, because packaged application folders may be read-only or replaced during upgrades.

Preferred default database location:

- Windows: `%LOCALAPPDATA%/InventoryFeedTool/inventory-feed-tool.sqlite3`
- macOS: `~/Library/Application Support/InventoryFeedTool/inventory-feed-tool.sqlite3`
- Linux: `${XDG_DATA_HOME}/inventory-feed-tool/inventory-feed-tool.sqlite3`, or `~/.local/share/inventory-feed-tool/inventory-feed-tool.sqlite3`

Tests should use temporary database paths and never touch the real app-data location.

## Schema Strategy

Use `PRAGMA user_version` for schema versioning.

Initial version: `1`

The initializer should:

1. Open the database.
2. Enable foreign keys.
3. Read `PRAGMA user_version`.
4. Apply migrations in order.
5. Set the final user version.

This is enough for early project needs without introducing a migration framework.

## Data Retention

Source offer snapshots may grow over time. The MVP should keep them because they are useful for troubleshooting. A later cleanup feature can add retention controls if real database size becomes a problem.

## Important Constraints

- Do not store raw distributor feed files in the database.
- Do not store distributor credentials.
- Do not store target-system credentials.
- Store file paths and source row references only as traceability metadata.
- Keep settings generic; do not hardcode a specific business or operator.

## Open Questions

No blocking questions for the first storage implementation.
