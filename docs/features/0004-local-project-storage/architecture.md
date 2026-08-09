# Architecture

## Design Direction

Use Python's standard-library `sqlite3` module and a small repository layer.

Proposed module layout:

```text
src/inventory_feed_tool/
  storage.py
```

The storage module should own:

- database path discovery
- connection setup
- schema initialization
- simple CRUD/repository operations
- JSON serialization for configuration snapshots

The ETL model should remain independent from SQLite. Feed adapters, aggregation, and exporters should receive model objects and repository objects rather than importing low-level SQL directly.

## Public API Shape

Proposed types/functions:

```python
def default_database_path() -> Path
def connect_database(path: Path | None = None) -> sqlite3.Connection
def initialize_database(connection: sqlite3.Connection) -> None

class LocalStore:
    @classmethod
    def open(cls, path: Path | None = None) -> LocalStore
    def close(self) -> None
    def save_setting(self, key: str, value: str) -> None
    def load_setting(self, key: str) -> str | None
    def save_run_configuration(self, configuration: RunConfiguration) -> None
    def load_run_configuration(self) -> RunConfiguration
    def create_export_run(...) -> int
    def upsert_external_product_mapping(...) -> None
    def find_external_product_mapping(...) -> ExternalProductMapping | None
    def record_source_offer_snapshot(...) -> int
    def upsert_source_override(...) -> None
```

The first implementation can keep arguments explicit instead of over-abstracting around repository classes.

## Schema

### `app_settings`

Stores simple app-level settings and serialized configuration defaults.

```text
key TEXT PRIMARY KEY
value TEXT NOT NULL
updated_at TEXT NOT NULL
```

Planned keys:

- `run_configuration.default`

### `export_runs`

Stores one conversion/export run.

```text
id INTEGER PRIMARY KEY AUTOINCREMENT
created_at TEXT NOT NULL
export_mode TEXT NOT NULL
output_folder TEXT
configuration_json TEXT NOT NULL
notes TEXT
```

### `external_product_mappings`

Stores known relationship between internal product identity and target-system product IDs. GoDaddy is the first supported target system.

```text
id INTEGER PRIMARY KEY AUTOINCREMENT
target_system TEXT NOT NULL
canonical_sku TEXT NOT NULL
upc TEXT
distributor TEXT
source_sku TEXT
external_product_id TEXT
last_seen_export_run_id INTEGER
created_at TEXT NOT NULL
updated_at TEXT NOT NULL
UNIQUE(target_system, canonical_sku)
FOREIGN KEY(last_seen_export_run_id) REFERENCES export_runs(id)
```

Lookup order for update mode:

1. Exact `target_system` and `canonical_sku`.
2. Exact `target_system` and UPC when present.

The exact GoDaddy export sync logic belongs to feature `0007-godaddy-export-sync`; this feature only provides the generic storage primitive.

### `source_offers`

Stores a snapshot of source offers observed during a run.

```text
id INTEGER PRIMARY KEY AUTOINCREMENT
export_run_id INTEGER NOT NULL
canonical_sku TEXT NOT NULL
upc TEXT
distributor TEXT NOT NULL
source_sku TEXT NOT NULL
unit_cost TEXT
calculated_price TEXT
quantity INTEGER
raw_quantity TEXT
availability_status TEXT
map_price TEXT
is_selected INTEGER NOT NULL DEFAULT 0
payload_json TEXT NOT NULL
created_at TEXT NOT NULL
FOREIGN KEY(export_run_id) REFERENCES export_runs(id)
```

Money values should be stored as text to preserve decimal precision.

`payload_json` should contain a compact serialized view of useful source offer metadata. It should not store raw full feed files.

### `source_overrides`

Stores user decisions for future source selection.

```text
id INTEGER PRIMARY KEY AUTOINCREMENT
target_system TEXT NOT NULL
canonical_sku TEXT NOT NULL
upc TEXT
preferred_distributor TEXT
preferred_source_sku TEXT
created_at TEXT NOT NULL
updated_at TEXT NOT NULL
UNIQUE(target_system, canonical_sku)
```

## Configuration Serialization

Use JSON for `RunConfiguration` persistence.

Rules:

- Enum values serialize to their string values.
- `Decimal` values serialize to strings.
- Missing future keys should fall back to current dataclass defaults.
- Unknown future keys should be ignored when loading, so older databases remain usable after small config changes.

## External Product Mapping Behavior

The tool owns `canonical_sku`, UPC, source identifiers, and matching records.

The target system owns its product IDs. For the first target, GoDaddy owns `PRODUCT ID`.

Storage rules:

- `external_product_id` may be null until learned from a target-system export.
- Do not generate or invent target-system product IDs.
- Upsert mappings by `target_system` and `canonical_sku`.
- Preserve UPC for fallback matching and manual review.

## Error Handling

Storage code should raise clear Python exceptions for programming/configuration errors.

For user-facing workflows, callers should catch those exceptions and convert them to validation messages or UI status messages in later features.

## Testing

Use temporary SQLite database files for tests.

Tests should cover:

- schema initialization is idempotent
- schema version is set
- settings save/load
- run configuration save/load
- export run creation
- external product mapping upsert/find by target system, SKU, and UPC
- source offer snapshot insert
- source override upsert/find
