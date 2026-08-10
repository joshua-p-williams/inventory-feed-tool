# Architecture

## Design Direction

Add a target-specific exporter package and a GoDaddy CSV exporter module.

Proposed module layout:

```text
src/inventory_feed_tool/
  exporters/
    __init__.py
    godaddy.py
```

The exporter should receive already-aggregated `CanonicalProduct` objects. It should not parse distributor feeds, aggregate source offers, or query SQLite directly.

## Core API

Proposed result dataclass:

```python
@dataclass(frozen=True)
class ExportedFile:
    path: Path
    row_count: int

@dataclass(frozen=True)
class GoDaddyExportResult:
    files: tuple[ExportedFile, ...]
    messages: tuple[ValidationMessage, ...] = ()
    products_seen: int = 0
    products_exported: int = 0
    products_skipped: int = 0
```

Proposed public function:

```python
def export_godaddy_csv(
    products: Iterable[CanonicalProduct],
    output_dir: Path,
    configuration: RunConfiguration | None = None,
    *,
    batch_size: int = 100,
    filename_prefix: str = "godaddy-import",
    product_id_lookup: ProductIdLookup | None = None,
) -> GoDaddyExportResult:
    ...
```

Proposed update-mode hook:

```python
class ProductIdLookup(Protocol):
    def find_product_id(self, product: CanonicalProduct) -> str | None:
        ...
```

The hook should exist so update-mode logic has an obvious insertion point later. `0007` should not implement storage-backed lookup.

## Export Modes

Use `RunConfiguration.export_mode`.

### New Import

- Supported in this feature.
- Leave `PRODUCT ID` blank.
- Write CSV rows for valid products with selected offers.

### Update Import

- Not fully supported in this feature.
- If `export_mode == update`, return a clear error message and do not write files.
- Reject update mode even if `product_id_lookup` is provided.
- Keep the lookup hook documented as the future insertion point for `0008`/`0009`.

This avoids accidentally generating partial update files before GoDaddy export sync and mapping coverage behavior are implemented.

## Batching

GoDaddy's documented bulk upload limit is 100 products.

Rules:

- Default batch size: `100`.
- Validate `batch_size > 0`.
- Split exported rows into batches of at most `batch_size`.
- Use deterministic file names:

```text
godaddy-import-001.csv
godaddy-import-002.csv
godaddy-import-003.csv
```

- Create `output_dir` if needed.
- Do not create empty CSV files when no rows are exportable.

## Column Order

Use this exact column order:

```text
SKU
EAN
UPC
GTIN
ISBN
TYPE
NAME
PRODUCT ID
VARIANT GROUP ID
SHORTCODE
MANUFACTURER
MODEL NUMBER
MSRP
BRAND
STATUS
PRICE
SALE PRICE
UNIT COST
ALLOW CUSTOM PRICE
ON-HAND QUANTITY
TRACK INVENTORY
ALLOW BACKORDER
DESCRIPTION
DISABLE SHIPPING
FREE SHIPPING
FIXED SHIPPING FEE
WEIGHT
LENGTH
WIDTH
HEIGHT
IMAGE URL
OPTION 1 NAME
OPTION 1 VALUE
OPTION 2 NAME
OPTION 2 VALUE
OPTION 3 NAME
OPTION 3 VALUE
```

## Field Mapping

| GoDaddy Column | Source |
| --- | --- |
| `SKU` | `product.identity.canonical_sku` |
| `EAN` | `product.identity.ean` |
| `UPC` | `product.identity.upc` |
| `GTIN` | `product.identity.gtin` |
| `ISBN` | `product.identity.isbn` |
| `TYPE` | `product.details.product_type` or `PHYSICAL` |
| `NAME` | `product.details.name` |
| `PRODUCT ID` | blank in new mode; future lookup in update mode |
| `VARIANT GROUP ID` | blank |
| `SHORTCODE` | blank |
| `MANUFACTURER` | `product.identity.manufacturer` |
| `MODEL NUMBER` | `product.identity.model_number` |
| `MSRP` | `selected_offer.pricing.msrp` |
| `BRAND` | `product.identity.brand` |
| `STATUS` | `product.details.status` or `ACTIVE` |
| `PRICE` | `selected_offer.pricing.calculated_price` |
| `SALE PRICE` | `selected_offer.pricing.sale_price` |
| `UNIT COST` | `selected_offer.pricing.unit_cost` |
| `ALLOW CUSTOM PRICE` | `false` |
| `ON-HAND QUANTITY` | `selected_offer.inventory.quantity` |
| `TRACK INVENTORY` | `selected_offer.inventory.track_inventory` |
| `ALLOW BACKORDER` | `selected_offer.inventory.allow_backorder` |
| `DESCRIPTION` | product description plus compliance notes |
| `DISABLE SHIPPING` | `selected_offer.shipping.disable_shipping` |
| `FREE SHIPPING` | `selected_offer.shipping.free_shipping` |
| `FIXED SHIPPING FEE` | `selected_offer.shipping.fixed_shipping_fee` |
| `WEIGHT` | `selected_offer.shipping.weight` |
| `LENGTH` | `selected_offer.shipping.length` |
| `WIDTH` | `selected_offer.shipping.width` |
| `HEIGHT` | `selected_offer.shipping.height` |
| `IMAGE URL` | `selected_offer.media.image_url` |
| `OPTION 1-3 NAME/VALUE` | blank |

If `RunConfiguration.images.include_image_urls` is false, leave `IMAGE URL` blank even when the selected offer has an image URL.

## Required Field Validation

Skip the product and attach a validation message if:

- `selected_offer` is missing
- `SKU` is blank
- `NAME` is blank
- `PRICE` is missing
- `ON-HAND QUANTITY` is missing
- `TYPE` is not `PHYSICAL`
- `STATUS` is not `ACTIVE`, `DRAFT`, or `ARCHIVED`

`CanonicalProduct` and `SourceOffer` dataclasses already enforce several of these at construction time, but the exporter should still validate defensively.

## SKU And Product ID Ownership

Export `SKU` from `CanonicalProduct.identity.canonical_sku` even in new-import mode. GoDaddy references are mixed on whether SKU can be autogenerated for all import paths, but the Websites + Marketing spreadsheet guidance requires SKU values and the local template includes the column.

Leave `PRODUCT ID` blank in new-import mode. The tool owns stable SKUs and matching keys; GoDaddy owns product IDs.

## Formatting

### Text

- Convert `None` to blank.
- Strip leading/trailing whitespace.
- Preserve internal line breaks in descriptions.

### Money

- Format `Decimal` values as plain decimal strings.
- No currency symbols.
- No thousands separators.
- Use up to two decimal places.
- Strip unnecessary trailing zeros, so `500.00` may export as `500` and `7.50` as `7.5`.

The downloaded Websites + Marketing formatting guidance allows numbers or decimals, with a maximum of two decimal places but decimals not required.

### Boolean

Use lowercase strings:

```text
true
false
```

This matches earlier local examples and is easy to test. If later GoDaddy testing requires uppercase, centralize the formatting helper.

The downloaded Websites + Marketing formatting guidance says boolean values are not case-sensitive and accepts true/false-style values. The local template sample uses lowercase `true` and `false`.

### Quantity

Use integer string values from selected offer inventory.

## Description Construction

Start with `product.details.description`.

Append compliance notes returned by:

```python
selected_offer.compliance.description_notes(configuration.compliance)
```

Use deterministic plain-text formatting:

```text
{description}

FFL required.
SOT required.
```

Do not duplicate a compliance note if the description already contains the same exact line.

## Validation Messages

Use `ValidationMessage.warning` for skipped product rows in new-import mode.

Use `ValidationMessage.error` for unsupported update mode in this feature.

Messages should include stable codes, such as:

- `godaddy_missing_selected_offer`
- `godaddy_missing_required_field`
- `godaddy_invalid_field_value`
- `godaddy_update_mode_not_supported`

## Tests

Tests should use hand-built `CanonicalProduct` and `SourceOffer` objects.

Coverage should include:

- header/column order
- one valid product row
- batch splitting at configurable small batch size
- default batch size behavior can be covered by helper tests
- missing selected offer skipped
- required field validation
- unsupported type/status validation
- new mode leaves `PRODUCT ID` blank
- update mode fails safely
- money formatting
- boolean formatting
- compliance notes appended
- image URL mapping
- image URL disabled by configuration
- no empty output file when every product is skipped
