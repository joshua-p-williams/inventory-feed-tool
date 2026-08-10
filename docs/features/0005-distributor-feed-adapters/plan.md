# Plan

1. Add `src/inventory_feed_tool/feeds/`.
2. Add shared feed parsing result helpers in `feeds/base.py`.
3. Implement Lipseys CSV adapter.
4. Implement Davidsons CSV adapter with optional quantity-file merge.
5. Add deterministic description-building helpers if needed.
6. Add tests using sanitized CSV fixtures.
7. Update README and changelog.

## Proposed Implementation Order

1. `FeedParseResult`
2. shared CSV/file validation helpers
3. Lipseys required column validation
4. Lipseys row-to-`SourceOffer` mapping
5. Lipseys image URL helper
6. Davidsons required column validation
7. Davidsons quantity file index
8. Davidsons row-to-`SourceOffer` mapping
9. Davidsons warehouse quantity merge
10. warning/error handling tests
11. adapter happy-path tests
12. README and changelog updates

## Locked Decisions

- This feature is file-based only.
- Use standard-library `csv.DictReader`.
- Do not copy real distributor feed data into the repository.
- Do not retrieve authenticated API or FTP feeds.
- Adapters produce `SourceOffer` objects and `ValidationMessage` output.
- Adapters do not group duplicate products.
- Adapters do not select a winning offer.
- Adapters do not write GoDaddy CSV rows.
- Adapters use `RunConfiguration.pricing` and `RunConfiguration.availability`.
- Adapters preserve extra fields in `attributes`.
- Lipseys image URLs are built from `IMAGENAME`.
- Davidsons image URLs remain blank for current samples.
- Davidsons quantity file is optional but preferred when supplied.
- Lipseys and Davidsons can be parsed independently; both distributors are not required for one run.
- Davidsons inventory CSV is required for Davidsons parsing.
- Davidsons quantity CSV cannot be used by itself because it lacks full product data.
- Davidsons quantity-file rows that do not match inventory rows are ignored for this feature, possibly reported later.
- Davidsons `MSP` should be treated as MAP when numeric and greater than zero for initial parsing.
- Missing UPC should warn and use a source-prefixed fallback SKU.
- Missing source SKU, product name, or unit cost should skip the affected row.
- A later UI wiring feature should add a separate optional Davidsons quantity CSV picker.

## Review Points Before Coding

No open review points remain for this feature.

## Future Feature Queue

1. `0006-source-aggregation-and-selection`
2. `0007-godaddy-csv-exporter`
3. `0008-godaddy-export-sync`
4. `0009-update-mode-export`
5. `0010-authenticated-feed-sources`
