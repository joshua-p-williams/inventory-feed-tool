# Research

## Prior Feature Decisions

From `0003-canonical-inventory-model`:

- GoDaddy is the first target export format.
- GoDaddy exporter should export canonical products, not raw distributor offers.
- Offer-specific columns such as price, cost, quantity, shipping details, and image URL come from `selected_offer`.
- `PRODUCT ID` is blank for new imports.
- Update mode requires externally learned GoDaddy `PRODUCT ID` mappings.
- The tool should never generate or invent GoDaddy `PRODUCT ID` values.
- Prices should be formatted as normal dollars/decimals, not cents.
- GoDaddy import supports one image URL per product.
- GoDaddy Websites + Marketing Commerce bulk CSV upload is limited to 100 products.
- Current research did not find a CSV-supported inquiry-only or "call for details" state.
- Allocated and unknown-quantity products should not be exported by default.
- Compliance flags should initially become description notes rather than excluding products.

From `0006-source-aggregation-and-selection`:

- Exporters should receive `CanonicalProduct` records from aggregation.
- Aggregation drops all-non-exportable groups from returned products.
- Returned products should normally have a selected offer.
- Exporters should still defend against `selected_offer=None` and report skipped products.

## GoDaddy References

Repo-safe reference summary:

- [GoDaddy product import reference](../../references/godaddy.md)

Official pages reviewed earlier:

- https://www.godaddy.com/help/catalog-import-starter-template-42984
- https://www.godaddy.com/help/import-products-from-a-csv-file-16581
- https://www.godaddy.com/help/format-my-online-store-product-spreadsheet-16580
- https://www.godaddy.com/help/manage-my-online-store-inventory-12384

Local downloaded copies were kept outside this repository under `../references/godaddy/`.

## Template Columns

The local GoDaddy product import template has these columns:

```text
SKU,EAN,UPC,GTIN,ISBN,TYPE,NAME,PRODUCT ID,VARIANT GROUP ID,SHORTCODE,MANUFACTURER,MODEL NUMBER,MSRP,BRAND,STATUS,PRICE,SALE PRICE,UNIT COST,ALLOW CUSTOM PRICE,ON-HAND QUANTITY,TRACK INVENTORY,ALLOW BACKORDER,DESCRIPTION,DISABLE SHIPPING,FREE SHIPPING,FIXED SHIPPING FEE,WEIGHT,LENGTH,WIDTH,HEIGHT,IMAGE URL,OPTION 1 NAME,OPTION 1 VALUE,OPTION 2 NAME,OPTION 2 VALUE,OPTION 3 NAME,OPTION 3 VALUE
```

## Export Implications

- Use Python standard-library `csv.DictWriter`.
- Use `newline=""` and UTF-8 encoding.
- Keep column order exactly as the template.
- Use one row per canonical product.
- Export `SKU` from `CanonicalProduct.identity.canonical_sku`.
- Leave variant and option columns blank for the first implementation.
- Leave `SHORTCODE` blank and allow GoDaddy to generate it unless later testing shows a need to populate it.
- Write `TYPE` as `PHYSICAL`.
- Write `STATUS` from `CanonicalProduct.details.status`, defaulting to `ACTIVE`.
- Write `ALLOW CUSTOM PRICE` as false when `PRICE` is populated.
- Write `TRACK INVENTORY` from selected offer inventory.
- Write `ALLOW BACKORDER` from selected offer inventory.
- Write normal decimal currency values without `$` or comma separators.

## SKU Decision

The downloaded GoDaddy references are not perfectly consistent across product areas:

- The Websites + Marketing spreadsheet-format page says SKU, name, and price must be present with values for each product.
- The catalog starter template page says GoDaddy can autogenerate SKU when adding a new product.

For this project, export `CanonicalProduct.identity.canonical_sku` into `SKU` for new imports. The local template includes `SKU`, the Websites + Marketing import guidance treats SKU as required, and a stable SKU is important for repeatable imports, duplicate prevention, reporting, and later update mapping.

This decision does not change `PRODUCT ID` behavior. New-import mode still leaves `PRODUCT ID` blank because GoDaddy owns that value.

## Update Mode Research

GoDaddy requires `PRODUCT ID` for updates to existing products. The next features are expected to:

- import a GoDaddy product export
- sync GoDaddy `PRODUCT ID` values into SQLite external product mappings
- enable update-mode export once mapping coverage and failure behavior are in place

For this feature, update mode should fail safely with a clear validation/error result. It should not write update CSV rows with blank or invented product IDs.

## Resolved Review Decisions

- Lowercase `true` and `false` are acceptable for `0007`. The local template uses lowercase values, and the downloaded Websites + Marketing formatting guidance says boolean values are not case-sensitive.
- Money formatting should strip unnecessary trailing zeros. GoDaddy allows numbers or decimals with up to two decimal places, so `500` and `7.5` are acceptable outputs.
- Update mode should be rejected in `0007` even if a product-ID lookup hook is passed. The hook is kept only to define the future insertion point.

## Description Notes

GoDaddy has no confirmed dedicated FFL/SOT/NFA import columns in the observed template. Description notes are the initial safe behavior.

Compliance notes should use `selected_offer.compliance.description_notes(configuration.compliance)`.

Description construction should start with `CanonicalProduct.details.description`, then append compliance notes if any. Keep formatting deterministic and plain text.
