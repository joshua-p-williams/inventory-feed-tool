# GoDaddy Product Import Reference

Reviewed: 2026-08-08 and 2026-08-09

## Source URLs

- https://www.godaddy.com/help/catalog-import-starter-template-42984
- https://www.godaddy.com/help/import-products-from-a-csv-file-16581
- https://www.godaddy.com/help/format-my-online-store-product-spreadsheet-16580
- https://www.godaddy.com/help/manage-my-online-store-inventory-12384

Local downloaded copies were kept in the parent project folder under `references/godaddy/` during research. Those downloaded pages are outside this repository; this repository keeps only this summary.

## Relevant Findings

- The local GoDaddy product import template appears to match GoDaddy's catalog import starter template field set.
- For first-time imports, GoDaddy owns `PRODUCT ID`; import rows should leave it blank so GoDaddy can assign it.
- Existing products require known `PRODUCT ID` values for update workflows.
- Websites + Marketing CSV import supports physical products.
- `TYPE` defaults to `PHYSICAL`.
- `STATUS` supports `ACTIVE`, `DRAFT`, and `ARCHIVED`.
- `ALLOW CUSTOM PRICE` should be false when price fields are present.
- Price fields use normal currency amounts, not cents. Examples are values like `7`, `7.50`, and `1000`.
- Product import supports one image URL per product during CSV import.
- Websites + Marketing Commerce bulk upload is documented with a 100-product limit.
- Inventory management supports tracking quantity, low-inventory alerts, and backorder behavior.
- No CSV-supported inquiry-only or "call for details" product state has been confirmed.

## Implementation Implications

- The exporter should batch GoDaddy CSV output into 100-product files.
- New-import mode should leave `PRODUCT ID` blank.
- Update mode should populate `PRODUCT ID` only from externally learned mappings.
- The tool should never generate or invent GoDaddy product IDs.
- Export prices should be formatted as decimal currency strings, not cents.
- Allocated or unknown-quantity distributor offers should not be exported as inquiry-only products unless a later confirmed GoDaddy workflow supports that safely.
- GoDaddy-specific external IDs should be stored through the generic `external_product_mappings` storage table with `target_system = "godaddy"`.
