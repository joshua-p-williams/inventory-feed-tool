# Feature: Import Output Quality Hardening

## Purpose

Fix issues found while analyzing a real full-size GoDaddy new-import output folder before adding update-mode workflows.

The current ETL run completes and produces structurally valid batch files, but the generated CSVs contain a few avoidable quality problems that should be corrected before the output is treated as production-ready website import data.

## Trigger

Analysis of a local full-size `results` output folder found:

- `138` GoDaddy CSV batch files.
- `13,750` exported products.
- Consistent `37`-column GoDaddy headers across every batch.
- No duplicate exported SKUs.
- `8,439` product groups intentionally dropped because no exportable offer existed.
- `22` exported Davidsons rows with invalid `UPC` value `##`.
- Money values that are numerically valid but not consistently formatted with two decimal places.
- Partial image coverage, especially blank Davidsons image URLs.

## In Scope

- Blank invalid or placeholder UPC values before GoDaddy export while preserving fallback canonical SKUs.
- Keep valid UPC values in the exported `UPC` column.
- Format money fields consistently with two decimal places in GoDaddy CSV output:
  - `MSRP`
  - `PRICE`
  - `SALE PRICE`
  - `UNIT COST`
  - `FIXED SHIPPING FEE`
- Add regression tests for invalid UPC handling and fixed money formatting.
- Add Davidsons image URL construction when an image can be inferred from public GalleryofGuns/Davidsons image hosting patterns.
- Preserve warnings or blanks when a Davidsons image URL cannot be inferred safely.
- Add an automated output-quality analysis helper or testable utility where useful.
- Regenerate or re-analyze full sample output after fixes.
- Update docs with the result of the hardening pass.

## Out of Scope

- GoDaddy product export sync and update-mode product ID mapping.
- Changing the source aggregation and selected-offer strategy.
- Listing products that are currently dropped as non-exportable.
- Authenticated distributor feed retrieval.
- Category mapping.

## Success Criteria

- Exported CSVs no longer contain `UPC=##`.
- Invalid/missing UPC rows still export with safe fallback SKUs when the product is otherwise exportable.
- Money fields use fixed two-decimal formatting where values are present.
- Davidsons rows receive image URLs when the known public Cloudinary pattern applies.
- Davidsons image construction does not block rows when images are unavailable or unverified.
- Existing GoDaddy exporter tests still pass.
- New regression tests cover the discovered issues.
- Full sample output analysis shows no duplicate SKUs, consistent headers, and corrected UPC/money output.

## Notes

Blank image URLs are acceptable for this feature. They should remain warnings or known limitations rather than blocking imports.

The large `no_exportable_offer` count is expected under current availability policy because zero, allocated, and unknown inventory are not exported by default.
