# Source Aggregation And Selection

## Purpose

Group parsed distributor `SourceOffer` records into `CanonicalProduct` records and choose one selected offer for each product according to explicit run configuration.

This feature is the bridge between feed adapters and target exporters. Feed adapters produce source-specific offers. Exporters should receive product-level records with a selected offer, so source-selection behavior is not duplicated in each target exporter.

## Scope

- Add an aggregation module for grouping `SourceOffer` records.
- Group offers by `identity.canonical_sku`.
- Preserve every source offer on resulting `CanonicalProduct` records that have an exportable selected offer.
- Choose `selected_offer` using `RunConfiguration.source_selection`.
- Respect `InventoryAvailability.is_exportable_by_default` during default selection.
- Drop product groups that have no exportable selected offer from the returned product list.
- Return validation messages for dropped groups so unavailable products do not disappear silently.
- Support source-selection strategies:
  - gross profit
  - quantity
  - distributor priority
- Support optional product-level source overrides as plain input data.
- Attach conflict messages when grouped offers disagree on important identity, detail, or pricing fields.
- Add tests using hand-built `SourceOffer` objects.

## Out Of Scope

- Reading distributor CSV files.
- Writing GoDaddy CSV files.
- Reading or writing SQLite storage.
- Building desktop UI controls.
- Syncing GoDaddy `PRODUCT ID` values.
- Persisting source-selection overrides.
- Manual review workflows.
- Authenticated distributor API or FTP retrieval.

Those remain separate features.

## Success Criteria

- Multiple offers with the same canonical SKU produce one `CanonicalProduct`.
- Offers with different canonical SKUs produce separate `CanonicalProduct` records.
- Selected offers are chosen deterministically.
- Non-exportable offers are not selected by default when exportable alternatives exist.
- If no exportable offer exists, the product group is dropped from `products` and reported with a warning.
- Gross-profit selection chooses the offer with the highest `calculated_price - unit_cost`.
- Quantity selection chooses the offer with the highest available quantity.
- Distributor-priority selection follows configured preferred distributor order.
- Product-level overrides can select a matching distributor/source SKU when allowed.
- Invalid or stale overrides produce warnings and fall back to configured automatic selection.
- Conflict messages are attached for meaningful cross-source disagreements.
- Tests do not depend on real distributor feed files.
