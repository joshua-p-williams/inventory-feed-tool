# Research

## Source

The hardening work is based on local analysis of a full generated output folder outside the repository:

```text
<workspace>\results
```

Analyzed from WSL as:

```text
<workspace>/results
```

Analysis date: 2026-08-11.

## Output Folder Summary

Files found:

- `138` GoDaddy CSV batch files.
- `conversion-log-20260810-235647.txt`.
- `conversion-log-latest.txt`.

The timestamped log and latest log had the same size, which confirms the latest convenience copy matched the durable run log for this run.

## Run Log Summary

The conversion log reported:

```text
Completed with warnings.

Rows seen: 29583
Rows skipped: 0
Offers parsed: 29583
Product groups: 22189
Product groups dropped: 8439
Products exported: 13750
Products skipped: 0
```

Feed-level counts:

```text
lipseys:
  Rows seen: 19012
  Rows skipped: 0
  Offers parsed: 19012
  Messages: 11

davidsons:
  Rows seen: 10571
  Rows skipped: 0
  Offers parsed: 10571
  Messages: 500
```

Message summary:

```text
WARNING no_exportable_offer (selected_offer): 8439
WARNING davidsons_approximate_quantity (Quantity_NC): 274
WARNING davidsons_approximate_quantity (Quantity_AZ): 163
WARNING davidsons_invalid_upc (UPC Code): 52
WARNING davidsons_missing_quantity_match (Item #): 11
WARNING lipseys_missing_upc (UPC): 11
```

## CSV Structure Findings

The generated CSV files were structurally consistent:

- `138` files.
- `13,750` product rows.
- `37` columns.
- `0` header mismatches.
- Row counts were `100` rows per file except the last file, which had `50` rows.
- No duplicate exported SKUs.
- `PRODUCT ID` was blank for every row, which is expected for new-import mode.

Required-ish exported fields had no blanks:

```text
SKU: 0 blank
TYPE: 0 blank
NAME: 0 blank
STATUS: 0 blank
PRICE: 0 blank
UNIT COST: 0 blank
ON-HAND QUANTITY: 0 blank
TRACK INVENTORY: 0 blank
DESCRIPTION: 0 blank
```

Expected all-blank columns for new-import/simple-product mode:

```text
EAN
GTIN
ISBN
PRODUCT ID
VARIANT GROUP ID
SHORTCODE
SALE PRICE
FIXED SHIPPING FEE
OPTION 1 NAME
OPTION 1 VALUE
OPTION 2 NAME
OPTION 2 VALUE
OPTION 3 NAME
OPTION 3 VALUE
```

## Problem: Invalid UPC Placeholder Exported

Analysis found:

```text
DUP_UPCS 1 [('##', 22)]
```

The `22` rows with `UPC=##` used fallback Davidsons SKUs such as:

```text
DAV-07718
DAV-1136250
DAV-1815
DAV-HGB-DAGGER
DAV-LBP/HEMI
```

This means fallback SKU behavior is working, but the invalid source UPC text still leaks into `ProductIdentity.upc` and then into the GoDaddy `UPC` export column.

### Current Code Finding

In `src/inventory_feed_tool/feeds/davidsons.py`, `_canonical_sku()` warns and returns a fallback SKU when UPC parsing fails. However, `_parse_row()` still passes the original `upc` value into `ProductIdentity(upc=upc)`.

This creates the inconsistent state:

- `canonical_sku = DAV-...`
- `upc = ##`

The exporter then faithfully writes `##` to the GoDaddy `UPC` column.

### Decision

For invalid UPCs:

- keep fallback canonical SKU behavior
- keep warning behavior
- blank `ProductIdentity.upc`
- do not export invalid placeholder values into `UPC`

This preserves product uniqueness without putting bad identifier data into the target import.

## Problem: Money Formatting Not Fixed-Width

Money fields are rounded but not fixed to two decimal places.

Findings:

```text
PRICE_NOT_TWO_DECIMAL: 2614
UNIT COST_NOT_TWO_DECIMAL: 5302
MSRP_NOT_TWO_DECIMAL: 6910
```

Examples:

```text
PRICE: 992.5
UNIT COST: 794
MSRP: 999
```

These are valid numeric values, but fixed two-decimal formatting is safer for CSV import and easier for operators to review.

### Current Code Finding

In `src/inventory_feed_tool/exporters/godaddy.py`, `_money()` quantizes to cents, then calls `_strip_decimal()`. `_strip_decimal()` removes insignificant trailing zeros, producing values such as `992.5` and `794`.

### Decision

GoDaddy money export fields should keep two decimal places when values are present.

Use formatting equivalent to:

```python
format(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), ".2f")
```

Do not change non-money decimal formatting for weight and dimensions unless a separate target-format reason is found.

## Problem: Davidsons Image URL Coverage

Findings:

```text
IMAGE URL blank: 6260
Valid Lipseys image URLs: 7490
Invalid image URLs: 0
Image domain: www.lipseyscloud.com
```

By SKU prefix:

```text
DAV: 22 / 22 blank image URLs
UPC: 6238 / 13728 blank image URLs
```

Blank image URLs are not considered blocking for this feature. Lipseys image URL construction is working where image data is present. Davidsons image support may need separate research if the feed provides enough information to construct public image URLs.

### Current Feed Findings

The Davidsons CSV sample has no explicit image URL or image filename column:

```text
"Item #","Item Description",MSP,"Retail Price","Dealer Price","Sale Price","Sale Ends",Quantity,"UPC Code",Manufacturer,"Gun Type","Model Series",Caliber,Action,Capacity,Finish,Stock,Sights,"Barrel Length","Overall Length",Features
```

The XML companion file similarly has no explicit media field in observed samples.

One row contains an image-like value in `Capacity`:

```text
row 5612
Item #: 5PS1545A23
Capacity: 5PS1545A23.jpg
```

This appears to be source-feed data leakage rather than a stable column contract. It is useful evidence that Davidsons image filenames may be item-number-based, but it should not be treated as a reliable feed field by itself.

### Public Website Findings

Davidsons' public FAQ says a GalleryofGuns online store can show "full color pictures of the firearms and their specifications."

Search/image results for a known sample item showed a public GalleryofGuns product page:

```text
https://www.galleryofguns.com/genie/default.aspx?item=16412
```

The corresponding image URL was:

```text
https://res.cloudinary.com/davidsons-inc/image/upload/media/catalog/product/1/6/16412.jpg
```

HTTP checks confirmed this URL returns:

```text
HTTP 200
content-type: image/jpeg
```

The pattern also resolved for another sample item:

```text
Item #: GERMMP40925
URL: https://res.cloudinary.com/davidsons-inc/image/upload/media/catalog/product/g/e/GERMMP40925.jpg
Result: HTTP 200 image/jpeg
```

The row with the image-like `Capacity` value also resolved:

```text
Item #: 5PS1545A23
URL: https://res.cloudinary.com/davidsons-inc/image/upload/media/catalog/product/5/p/5PS1545A23.jpg
Result: HTTP 200 image/jpeg
```

The inferred pattern is:

```text
https://res.cloudinary.com/davidsons-inc/image/upload/media/catalog/product/<first-char-lower>/<second-char-lower>/<Item #>.jpg
```

Examples:

```text
16412        -> 1/6/16412.jpg
GERMMP40925  -> g/e/GERMMP40925.jpg
5PS1545A23   -> 5/p/5PS1545A23.jpg
```

### Caveats

The inferred pattern is not guaranteed for every item.

Observed caveats:

- A mixed alphanumeric Glock item, `PV1950S03XMOS`, did not resolve through the naive pattern during an HTTP check.
- GalleryofGuns product pages are protected by Cloudflare for scripted access, so automated scraping of product pages is not a good dependency.
- Some item numbers contain slash or other URL-sensitive characters. These need careful handling or should be left blank if the image public ID cannot be constructed safely.
- The CSV feed does not explicitly grant a per-row image URL, so this should remain a best-effort construction based on public hosting evidence.

### Decision

Davidsons image URL construction is now in scope for this hardening feature.

Initial behavior:

- construct a best-effort Cloudinary image URL from `Item #`
- use it as `ProductMedia.image_url` when image URLs are enabled
- do not block rows if image availability cannot be validated
- optionally support validation later, controlled by `ImagePolicy.validate_image_urls`
- keep `ProductMedia.image_source = "davidsons_cloudinary_item_number"` or similar source metadata

The implementation should not scrape GalleryofGuns pages. It should only construct deterministic image URLs from source item numbers and preserve a warning/log path for future validation improvements.

## Availability Drops

The large `no_exportable_offer` count is expected under the current conservative availability policy:

```text
WARNING no_exportable_offer (selected_offer): 8439
```

This is not a bug in this feature. It means product groups were created but all offers were non-exportable under the current policy, such as zero, allocated, or unknown inventory.

## Additional Observations

All exported products had:

```text
STATUS: ACTIVE
TYPE: PHYSICAL
TRACK INVENTORY: true
ALLOW BACKORDER: false
```

Price checks found:

```text
PRICE_BELOW_COST: 0
```

This supports keeping the current pricing behavior and focusing this feature on exported field quality.

## Post-Fix Verification

After implementation, a full sample conversion was regenerated to a temporary output folder outside the repository.

The conversion still matched the previous run counts:

```text
Files: 138
Rows: 13750
Row count min/max: 50 / 100
Header mismatches: 0
Duplicate SKUs: 0
```

Corrected UPC findings:

```text
UPC=## count: 0
Hash-wrapped UPC count: 0
Non-digit UPC sample: []
Blank UPC count: 22
```

The `22` blank UPC rows correspond to previously invalid Davidsons UPC placeholders. They now retain fallback `DAV-...` SKUs without exporting invalid `UPC` values.

Corrected money findings:

```text
MSRP not two decimals: 0
PRICE not two decimals: 0
SALE PRICE not two decimals: 0
UNIT COST not two decimals: 0
FIXED SHIPPING FEE not two decimals: 0
```

Image coverage findings:

```text
Blank images: 43
Invalid image URL syntax: 0
Lipseys image URLs: 7490
Davidsons Cloudinary image URLs: 6217
```

Compared to the original output analysis, blank images decreased from `6260` to `43`.

By exported SKU prefix:

```text
DAV: 6 blank / 22 exported
UPC: 37 blank / 13728 exported
```

Some `UPC-...` products have Davidsons-selected offers and now receive Davidsons Cloudinary URLs even though their canonical SKU is UPC-based.

Sample generated Davidsons URLs:

```text
DAV-07718 -> https://res.cloudinary.com/davidsons-inc/image/upload/media/catalog/product/0/7/07718.jpg
DAV-1136250 -> https://res.cloudinary.com/davidsons-inc/image/upload/media/catalog/product/1/1/1136250.jpg
DAV-HGB-DAGGER -> https://res.cloudinary.com/davidsons-inc/image/upload/media/catalog/product/h/g/HGB-DAGGER.jpg
```

The URLs are syntactically valid and deterministic. The tool still does not perform live image existence checks during normal conversion.
