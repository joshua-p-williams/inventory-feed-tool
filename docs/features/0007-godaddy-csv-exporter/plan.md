# Plan

1. Add `src/inventory_feed_tool/exporters/`.
2. Add `exporters/godaddy.py`.
3. Define GoDaddy column constants.
4. Define `ExportedFile` and `GoDaddyExportResult`.
5. Define update-mode lookup protocol/hook.
6. Implement row validation.
7. Implement value formatting helpers.
8. Implement description/compliance note formatting.
9. Implement product-to-row mapping.
10. Implement CSV writing and batching.
11. Add unit tests with hand-built products.
12. Update README and changelog.

## Proposed Implementation Order

1. package structure
2. column constants
3. result dataclasses
4. formatting helpers
5. description helper
6. selected-offer validation
7. product row builder
8. batching helper
9. CSV writer
10. public `export_godaddy_csv`
11. tests
12. README and changelog updates

## Locked Decisions

- Exporter consumes `CanonicalProduct` records.
- Exporter does not parse distributor feeds.
- Exporter does not aggregate source offers.
- Exporter does not import or query SQLite.
- New-import mode is supported first.
- New-import mode leaves `PRODUCT ID` blank.
- New-import mode exports `SKU` from `CanonicalProduct.identity.canonical_sku`.
- Update mode fails safely in this feature.
- Update mode is rejected even if a product-ID lookup hook is passed.
- Define update-mode hooks without implementing storage-backed mapping lookup.
- The tool never generates or invents GoDaddy `PRODUCT ID` values.
- Default batch size is `100`.
- Do not write empty CSV files when no rows are exportable.
- Use exact GoDaddy template column order.
- Use selected offer for price, unit cost, quantity, shipping, and image URL.
- Respect `RunConfiguration.images.include_image_urls`.
- Skip unsupported GoDaddy `TYPE` and `STATUS` values.
- Format money as normal decimal currency, not cents.
- Strip unnecessary trailing zeros from money values.
- Format booleans as lowercase `true` and `false`.
- Append compliance notes to description according to `RunConfiguration.compliance`.
- Leave variant/option columns blank.

## Review Points Before Coding

No open review points remain for this feature.

## Future Feature Queue

1. `0008-godaddy-export-sync`
2. `0009-update-mode-export`
3. `0010-authenticated-feed-sources`
