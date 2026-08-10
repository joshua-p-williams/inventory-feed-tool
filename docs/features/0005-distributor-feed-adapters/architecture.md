# Architecture

## Design Direction

Add feed adapter modules that translate source CSV rows into `SourceOffer` objects.

Proposed module layout:

```text
src/inventory_feed_tool/
  feeds/
    __init__.py
    base.py
    lipseys.py
    davidsons.py
```

The adapters should use only standard-library CSV parsing. They should not depend on pandas or external ETL packages.

## Core API

### `FeedParseResult`

Represents the result of parsing one distributor feed.

```python
@dataclass(frozen=True)
class FeedParseResult:
    distributor: str
    source_files: tuple[str, ...]
    offers: tuple[SourceOffer, ...]
    messages: tuple[ValidationMessage, ...] = ()
    rows_seen: int = 0
    rows_skipped: int = 0
```

### Adapter Functions

```python
def parse_lipseys_csv(path: Path, configuration: RunConfiguration) -> FeedParseResult

def parse_davidsons_inventory_csv(
    inventory_path: Path,
    configuration: RunConfiguration,
    quantity_path: Path | None = None,
) -> FeedParseResult
```

The first implementation can use functions instead of class hierarchies. If additional distributors create repeated behavior later, we can introduce a protocol or base class.

## Supported Input Combinations

Adapters should support independent distributor parsing:

- Lipseys CSV only.
- Davidsons inventory CSV only.
- Davidsons inventory CSV plus Davidsons quantity CSV.
- Lipseys CSV plus Davidsons inventory CSV, with or without Davidsons quantity CSV, when a later orchestration layer calls both adapters in one run.

Invalid combination:

- Davidsons quantity CSV by itself. The quantity file has warehouse quantities but not enough product data to create `SourceOffer` objects.

The desktop UI currently has one Davidsons file picker and one Lipseys file picker. A later UI wiring feature should split Davidsons inputs into:

- Davidsons inventory CSV.
- Davidsons quantity CSV, optional and enabled/recommended when Davidsons inventory is selected.

UI validation should require at least one source feed: Lipseys CSV or Davidsons inventory CSV. It should not require both distributors.

## Adapter Responsibilities

Adapters should:

- Open CSV files with `utf-8-sig` and `newline=""`.
- Use `csv.DictReader`.
- Validate required columns before row parsing.
- Parse each row into `SourceOffer`.
- Attach row-level warnings where data is recoverable.
- Skip only rows that cannot produce a usable offer.
- Preserve extra source fields in `attributes`.
- Use `build_product_pricing` with the provided `RunConfiguration.pricing`.
- Use `parse_availability` with the provided `RunConfiguration.availability`.
- Include source file and row number in `SourceInfo`.

Adapters should not:

- Group duplicate products.
- Select a winning distributor/source offer.
- Write GoDaddy CSV files.
- Store raw rows in SQLite.
- Retrieve files from authenticated APIs or FTP.
- Decide business policy outside the provided `RunConfiguration`.

## Required Row Fields

Adapters should skip a row with an error message if the row is missing:

- source SKU
- product name/description usable as `ProductDetails.name`
- unit cost
- both UPC and source SKU fallback identity

UPC is strongly preferred but not required. If UPC is absent, use a source-prefixed canonical SKU fallback.

## Lipseys Mapping

### Identity

| Model Field | Lipseys Column |
| --- | --- |
| `source.distributor` | `lipseys` |
| `source.source_sku` | `ITEMNO` |
| `identity.canonical_sku` | `UPC-{UPC}` when UPC exists, otherwise `LIP-{ITEMNO}` |
| `identity.upc` | `UPC` |
| `identity.manufacturer` | `MANUFACTURER` |
| `identity.brand` | `MANUFACTURER` |
| `identity.model_number` | `MANUFACTURERMODELNO` |
| `identity.model_name` | `MODEL` |

### Details

| Model Field | Lipseys Column |
| --- | --- |
| `details.name` | prefer `DESCRIPTION1`, append/consider `DESCRIPTION2` if needed |
| `details.description` | source descriptions plus important attributes |
| `details.product_type` | `PHYSICAL` |
| `details.category` | `ITEMTYPE` |
| `details.family` | `FAMILY` |
| `details.status` | `ACTIVE` |

### Pricing

| Model Field | Lipseys Column |
| --- | --- |
| `pricing.unit_cost` | prefer `CURRENTPRICE`, fallback `PRICE` |
| `pricing.msrp` | `MSRP` |
| `pricing.map_price` | `RETAILMAP` |
| `pricing.retail_price` | optional source retail-like values if available |
| `pricing.calculated_price` | shared pricing helper |

`ONSALE` and source sale-related data should be preserved as attributes. The current pricing profile defaults ignore source sale pricing unless a later feature enables it.

### Availability

| Model Field | Lipseys Column |
| --- | --- |
| `inventory.quantity` / `status` | `QUANTITY` plus `ALLOCATED` |
| `inventory.raw_quantity` | `QUANTITY` |
| `inventory.allow_backorder` | from `RunConfiguration.availability.allow_backorder` |

If `ALLOCATED` is truthy, parse the offer as allocated even if `QUANTITY` contains a number.

`CANDROPSHIP` should be preserved in `attributes` only.

### Shipping

| Model Field | Lipseys Column |
| --- | --- |
| `shipping.weight` | prefer `SHIPPINGWEIGHT`, fallback `WEIGHT` |
| `shipping.length` | prefer `PACKAGELENGTH`, fallback `ITEMLENGTH` |
| `shipping.width` | prefer `PACKAGEWIDTH`, fallback `ITEMWIDTH` |
| `shipping.height` | prefer `PACKAGEHEIGHT`, fallback `ITEMHEIGHT` |

### Compliance

| Model Field | Lipseys Column |
| --- | --- |
| `compliance.ffl_required` | `FFLREQUIRED` |
| `compliance.sot_required` | `SOTREQUIRED` |

### Media

| Model Field | Lipseys Column |
| --- | --- |
| `media.image_name` | `IMAGENAME` |
| `media.image_url` | constructed public Lipseys image URL |
| `media.image_source` | `lipseys` |

## Davidsons Mapping

### Identity

| Model Field | Davidsons Column |
| --- | --- |
| `source.distributor` | `davidsons` |
| `source.source_sku` | `Item #` |
| `identity.canonical_sku` | `UPC-{UPC Code}` when UPC exists, otherwise `DAV-{Item #}` |
| `identity.upc` | `UPC Code` |
| `identity.manufacturer` | `Manufacturer` |
| `identity.brand` | `Manufacturer` |
| `identity.model_number` | `Item #` unless a better model number appears later |
| `identity.model_name` | `Model Series` |

### Details

| Model Field | Davidsons Column |
| --- | --- |
| `details.name` | `Item Description` |
| `details.description` | source description plus important attributes |
| `details.product_type` | `PHYSICAL` |
| `details.category` | `Gun Type` |
| `details.family` | `Model Series` |
| `details.status` | `ACTIVE` |

### Pricing

| Model Field | Davidsons Column |
| --- | --- |
| `pricing.unit_cost` | `Dealer Price` |
| `pricing.msrp` | `Retail Price` |
| `pricing.map_price` | `MSP` when numeric and greater than zero |
| `pricing.retail_price` | `Retail Price` |
| `pricing.sale_price` | parsed but ignored by default pricing profile |
| `pricing.calculated_price` | shared pricing helper |

`Sale Price` and `Sale Ends` should be preserved when parseable, but source sale pricing is ignored unless a later feature enables it.

### Availability

If a Davidsons quantity file is provided:

1. Join by `Item #` to quantity file `Item_Number`.
2. Parse `Quantity_NC` and `Quantity_AZ`.
3. Sum known exact/approximate available lower-bound quantities.
4. If no warehouse has positive known availability and any warehouse is allocated, final availability is allocated.
5. If no warehouse has positive known availability and any warehouse is unknown/call-for-availability, final availability is unknown.
6. If no warehouse quantity row exists, fallback to inventory file `Quantity` and attach a warning.

If no quantity file is provided, parse inventory file `Quantity`.

Davidsons does not backorder according to public research. The adapter should still set `allow_backorder` from `RunConfiguration.availability`, but the default policy is false.

### Shipping

Current Davidsons samples do not contain weight/dimension fields. Leave shipping fields blank/defaulted.

### Compliance

Current Davidsons samples do not contain explicit FFL/SOT columns. Firearm-like category values can be preserved in attributes for later compliance handling, but the adapter should not infer legal flags without a reliable source field.

### Media

Current Davidsons samples do not contain image fields. Leave media fields blank/defaulted.

## Warnings And Errors

Use `ValidationMessage.warning` for recoverable issues:

- Missing UPC with source-SKU fallback.
- Missing optional image.
- Missing Davidsons quantity match when a quantity file is provided.
- Invalid optional numeric field.
- Approximate quantity such as `99+`.

Use `ValidationMessage.error` and skip the row for blocking issues:

- Missing source SKU.
- Missing product name.
- Missing or invalid unit cost.
- Missing required columns at the file level.

## Description Construction

Adapters should create a basic description from the source description fields and high-value attributes. The final target-specific product description format belongs to the GoDaddy exporter feature.

For this feature, descriptions should be plain text and deterministic.

## Tests

Tests should use hand-written, sanitized CSV strings covering:

- valid Lipseys row
- Lipseys-only parse result
- Lipseys missing UPC fallback SKU
- Lipseys allocated row
- Lipseys image URL construction
- valid Davidsons row without quantity file
- Davidsons-only parse result
- Davidsons row with quantity file merge
- rejection or validation for Davidsons quantity file without inventory file at the orchestration/UI layer
- Davidsons `A*`, `99+`, and missing quantity match
- invalid rows skipped with messages
- pricing behavior driven by supplied configuration
