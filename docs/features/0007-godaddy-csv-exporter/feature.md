# GoDaddy CSV Exporter

## Purpose

Export selected `CanonicalProduct` records into GoDaddy Websites + Marketing product import CSV files.

This feature creates the first target exporter. It should support new-product import mode end to end and define the hooks needed for later update-mode export.

## Scope

- Add a GoDaddy exporter module.
- Export `CanonicalProduct` records that have a `selected_offer`.
- Use the GoDaddy product import template column order.
- Support new-import mode by leaving `PRODUCT ID` blank.
- Define update-mode hooks without implementing GoDaddy product export sync.
- Split output into 100-product CSV batches.
- Format money as normal currency amounts, not cents.
- Format booleans consistently for GoDaddy CSV fields.
- Use selected offer fields for price, cost, quantity, shipping, and image URL.
- Add compliance description notes according to `RunConfiguration.compliance`.
- Produce validation messages for skipped products and unsupported update-mode paths.
- Add unit tests with hand-built canonical products.

## Out Of Scope

- Parsing distributor CSV files.
- Aggregating source offers.
- Reading or writing SQLite storage.
- Importing GoDaddy product exports.
- Looking up GoDaddy `PRODUCT ID` mappings from storage.
- Desktop UI wiring.
- Authenticated GoDaddy APIs.
- Product variants/options beyond blank option columns.
- Category/storefront taxonomy mapping beyond fields present in the template.

Those remain separate features.

## Success Criteria

- Exporter writes GoDaddy CSV files with the exact expected columns.
- New-import mode leaves `PRODUCT ID` blank.
- Products are batched into files of at most 100 rows.
- Products without `selected_offer` are skipped with validation messages.
- Required export fields are validated before writing rows.
- Unsupported GoDaddy field values are skipped before writing rows.
- Prices, cost, MSRP, sale price, shipping fee, weight, and dimensions are formatted as decimal strings.
- `TYPE`, `STATUS`, `ALLOW CUSTOM PRICE`, `TRACK INVENTORY`, `ALLOW BACKORDER`, `DISABLE SHIPPING`, and `FREE SHIPPING` are populated from model/defaults.
- FFL/SOT/NFA description notes are appended when configured.
- Image URL comes from the selected offer.
- Image URL is blank when `RunConfiguration.images.include_image_urls` is false.
- Update mode fails safely with a clear validation message until mapping support exists.
- Tests do not depend on real distributor feed files.
