# Research

## Prior Feature Decisions

From `0003-canonical-inventory-model`:

- Feed adapters produce `SourceOffer` objects.
- Aggregation groups source offers into `CanonicalProduct` objects.
- The same UPC can appear in multiple distributor feeds with different source SKUs, cost, quantity, MAP, shipping data, and source descriptions.
- UPC-based canonical SKUs are the default when UPC is present.
- Source-prefixed fallback SKUs are used when UPC is missing.
- The GoDaddy exporter should export canonical products, not raw distributor rows.
- Offer-specific export fields such as price, cost, quantity, shipping, and image should come from `selected_offer`.
- Source selection should preserve all offers and choose one selected offer for export.
- Default source selection should exclude zero-quantity, allocated, and unknown-quantity offers unless policy or override permits them.
- Estimated gross profit is:

```text
selected_export_price - distributor_unit_cost
```

From `0004-local-project-storage`:

- SQLite stores source offer snapshots and source-selection overrides.
- Source overrides are scoped by target system and canonical SKU.
- Storage should stay separate from the ETL model.
- Aggregation/selection code should receive repository data rather than import low-level SQL.

From `0005-distributor-feed-adapters`:

- Lipseys and Davidsons adapters can run independently.
- Adapters preserve availability status and source warnings.
- Adapters do not aggregate, select, export, or sync.
- Adapters harden malformed UPCs and quantities into warnings where possible.

## Sample Data Implications

Repo-safe reference summaries:

- [Local sample feed shapes](../../references/sample-feed-shapes.md)
- [Lipseys reference](../../references/lipseys.md)
- [Davidsons reference](../../references/davidsons.md)

Earlier sample analysis found meaningful UPC overlap between Lipseys and Davidsons. That confirms aggregation cannot be skipped before export, because exporting raw offers would create duplicate website products for the same UPC.

Important observed source differences:

- Lipseys and Davidsons often use different source item numbers for the same UPC.
- Unit cost can differ by distributor.
- Calculated price can differ when MAP, cost, or pricing inputs differ.
- Quantity can differ by distributor.
- Lipseys provides image URLs from `IMAGENAME`; current Davidsons samples do not.
- Lipseys provides explicit FFL/SOT flags; current Davidsons samples do not.

## Selection Policy Implications

Default behavior should prefer offers that can be safely sold online now. That means automatic selection should consider only offers where:

- `offer.inventory.is_exportable_by_default` is true.
- `offer.inventory.quantity` is positive for the current default availability policy.
- The offer has no blocking validation condition from earlier parsing.

Current `SourceOffer` stores warnings but does not store row-level blocking errors because feed adapters skip rows that cannot produce usable offers. Therefore, `0006` can initially treat all received offers as structurally usable and rely on availability/exportability to filter candidates.

## Override Implications

SQLite has storage primitives for source overrides, but the aggregation module should not depend on SQLite. The cleaner boundary is:

```text
LocalStore -> optional SourceSelectionOverride values -> aggregation service
```

This keeps aggregation deterministic and easy to test. A later UI/storage feature can decide when and how to load overrides.

## Conflict Detection

The aggregation step is the first point where the tool can compare multiple distributors for one canonical product.

Useful initial conflict checks:

- manufacturer differs
- brand differs
- model number differs
- model name differs
- product name differs meaningfully
- category differs
- MAP differs

Conflicts should be warnings, not hard errors, for the first implementation. They should preserve the selected product and all offers so a later UI/report can show what differed.

## Resolved Review Decisions

- Aggregation overrides stay target-neutral. Storage may scope overrides by target system, but orchestration is responsible for loading relevant target-system overrides before calling aggregation.
- Product groups with no exportable offer are dropped from returned products and reported through aggregation-level warnings.
- MAP conflicts should warn only when two or more nonblank MAP values differ. Blank MAP from one source and nonblank MAP from another source is not a conflict by itself.
- Do not collapse tiny name differences with fuzzy matching in this feature; compare normalized exact strings and keep the rule predictable.
- Overrides should not select otherwise non-exportable offers in this feature. Allow that only if a future manual-review UI adds an explicit unsafe override mode.
