# Architecture

## Design Direction

Use a small set of standard-library dataclasses for the canonical model.

The model should avoid feed-specific field names. Feed adapters translate source rows into source offers. Aggregation groups source offers into canonical products. Export adapters translate canonical products and their selected source offers into target formats such as GoDaddy CSV.

Proposed module layout:

```text
src/inventory_feed_tool/
  models.py
  parsing.py
  pricing.py
  validation.py
```

Potential future expansion:

```text
src/inventory_feed_tool/
  feeds/
    lipseys.py
    davidsons.py
  exporters/
    godaddy.py
```

## Core Pipeline

The model should represent distributor feed rows as offers, not final website products.

```text
RunConfiguration
  -> Distributor source rows
  -> SourceOffer
  -> grouped by ProductIdentity into CanonicalProduct
  -> configured pricing, availability, and source selection choose selected_offer
  -> ExportProduct / GoDaddy CSV row
```

This matters because the same UPC can appear in multiple feeds. Each feed row may have different cost, stock, MAP, shipping data, and source-specific descriptions. Keeping all offers lets the tool choose the best source for each export run without losing data.

Feed adapters should parse source rows into neutral `SourceOffer` objects. They should not make business decisions such as markup percentage, MAP behavior, whether allocated products are allowed, or which distributor wins a conflict. Those decisions belong to explicit configuration/policy objects passed into later pipeline steps.

## Core Types

### `Money`

Use `decimal.Decimal` directly for money values. Keep parsing/formatting helpers separate from the model.

### `RunConfiguration`

Represents the operator-controlled choices for one conversion run.

```python
@dataclass(frozen=True)
class RunConfiguration:
    export_mode: ExportMode
    pricing: PricingProfile
    availability: AvailabilityPolicy
    source_selection: SourceSelectionPolicy
    images: ImagePolicy
    compliance: CompliancePolicy
```

This object should be passed into pricing, filtering, source selection, and exporter steps. It should also be persistable later so the UI can restore the last-used configuration.

### `ExportMode`

Values:

- `new`: generate new GoDaddy product import rows with blank `PRODUCT ID`.
- `update`: generate GoDaddy update rows using known `PRODUCT ID` mappings.

### `PricingProfile`

Fields:

- `markup_percent`
- `map_mode`: `respect` or `ignore`
- `sale_price_mode`: `ignore`, `use_source_sale`, or `future_manual`
- `rounding_mode`: for example `nearest_cent`, `nearest_dollar`, or `charm_99`

Initial defaults:

- `markup_percent`: `25`
- `map_mode`: `respect`
- `sale_price_mode`: `ignore`
- `rounding_mode`: `nearest_cent`

Confirmed pricing behavior:

- Calculate the normal price from distributor unit cost plus the configured markup percentage.
- If distributor MAP is present and `map_mode` is `respect`, use MAP when the markup price would be lower than MAP.
- If no MAP is present, do not try to infer MAP from other fields; use the configured markup calculation and let the operator handle exceptions.
- Do not use distributor sale data in the first pricing behavior unless a later feature explicitly enables and tests it.

### `AvailabilityPolicy`

Fields:

- `include_zero_quantity`
- `include_allocated`
- `include_unknown_quantity`
- `approximate_quantity_floor`
- `allow_backorder`

Initial defaults:

- `include_zero_quantity`: `false`
- `include_allocated`: `false`
- `include_unknown_quantity`: `false`
- `approximate_quantity_floor`: `0`
- `allow_backorder`: `false`

### `SourceSelectionPolicy`

Fields:

- `strategy`: `gross_profit`, `quantity`, or `distributor_priority`
- `preferred_distributors`: ordered distributor identifiers
- `allow_manual_overrides`

Initial defaults:

- `strategy`: `gross_profit`
- `preferred_distributors`: empty until configured
- `allow_manual_overrides`: `true`

### `ImagePolicy`

Fields:

- `include_image_urls`
- `missing_image_behavior`: `warn`, `blank`, or `block_row`
- `validate_image_urls`

Initial defaults:

- `include_image_urls`: `true`
- `missing_image_behavior`: `warn`
- `validate_image_urls`: `false`

### `CompliancePolicy`

Fields:

- `ffl_required_behavior`: `description_note`, `exclude`, or `ignore`
- `sot_required_behavior`: `description_note`, `exclude`, or `ignore`
- `nfa_item_behavior`: `description_note`, `exclude`, or `ignore`

Initial defaults:

- `ffl_required_behavior`: `description_note`
- `sot_required_behavior`: `description_note`
- `nfa_item_behavior`: `description_note`

### `SourceOffer`

Represents one distributor's listing/offer for a product.

```python
@dataclass(frozen=True)
class SourceOffer:
    source: SourceInfo
    identity: ProductIdentity
    details: ProductDetails
    pricing: ProductPricing
    inventory: InventoryAvailability
    shipping: ShippingDetails
    compliance: ComplianceFlags
    media: ProductMedia
    attributes: dict[str, str]
    warnings: tuple[ValidationMessage, ...] = ()
```

Feed adapters should produce `SourceOffer` objects.

### `CanonicalProduct`

Represents one sellable product grouped from one or more source offers.

```python
@dataclass(frozen=True)
class CanonicalProduct:
    identity: ProductIdentity
    details: ProductDetails
    offers: tuple[SourceOffer, ...]
    selected_offer: SourceOffer | None = None
    conflicts: tuple[ConflictMessage, ...] = ()
    warnings: tuple[ValidationMessage, ...] = ()
```

The GoDaddy exporter should export canonical products. Offer-specific columns such as price, cost, quantity, and shipping details should come from `selected_offer`.

### `ConflictMessage`

Fields:

- `severity`: `info`, `warning`, or `error`
- `code`
- `message`
- `field`
- `offer_sources`: distributors/source SKUs involved

Conflict messages belong to canonical products because they usually compare multiple source offers.

### `SourceInfo`

Fields:

- `distributor`: for example `lipseys` or `davidsons`
- `source_file`: optional path or display name
- `source_sku`: distributor item number
- `source_row_number`: optional CSV row number
- `raw_identifier`: optional fallback identifier

Reason: GoDaddy needs one exported `SKU`, but duplicate handling, source selection, and traceability need to know where each source offer came from.

### `ProductIdentity`

Fields:

- `canonical_sku`: internal/export SKU for the sellable product
- `upc`
- `ean`
- `gtin`
- `isbn`
- `manufacturer`
- `brand`
- `model_number`
- `model_name`

Initial SKU strategy should be stable and product-oriented, not selected-offer-oriented. Use a UPC-based SKU when UPC is present, for example `UPC-736676037018`. If UPC is absent, use a source-prefixed fallback such as `DAV-PDSS2028`.

Using a product-oriented SKU avoids creating separate GoDaddy products for the same UPC when it appears in multiple feeds.

Plain-English rationale: distributor item numbers identify a distributor's offer, not necessarily the product itself. If Lipseys and Davidsons both sell the same product, they may use different item numbers but share the same UPC. A UPC-based canonical SKU means the exported GoDaddy product remains one product, while the middle model can still keep each distributor's source SKU on its `SourceOffer`.

### `ProductDetails`

Fields:

- `name`
- `description`
- `product_type`
- `category`
- `family`
- `status`

`product_type` should represent website/product type, not necessarily firearm type. For GoDaddy, exported `TYPE` will be `PHYSICAL`.

`category` and `family` preserve source taxonomy such as Lipseys `ITEMGROUP` or Davidsons `Gun Type`.

### `ProductPricing`

Fields:

- `unit_cost`
- `msrp`
- `map_price`
- `retail_price`
- `sale_price`
- `sale_ends`
- `calculated_price`
- `pricing_reason`

Pricing should be driven by `RunConfiguration.pricing`, not hardcoded into feed adapters or exporters.

```text
markup_price = unit_cost * (1 + markup_percent / 100)
calculated_price = max(markup_price, map_price) when MAP mode is respect and MAP exists and is greater than zero
otherwise calculated_price = markup_price
```

The UI should eventually allow the operator to change pricing options per run, with the last used values stored in SQLite. The model should store the resulting `calculated_price` and `pricing_reason`, but should not assume that 25 percent is permanently correct.

GoDaddy export formatting should use plain currency amounts with up to 2 decimal places, not cents. For example, five hundred dollars should export as `500` or `500.00`, not `50000`.

### `InventoryAvailability`

Fields:

- `status`: `available`, `out_of_stock`, `allocated`, `unknown`, or `discontinued`
- `quantity`
- `raw_quantity`
- `track_inventory`
- `allow_backorder`
- `availability_note`
- `is_exportable_by_default`

Quantity parsing should preserve both the normalized quantity and the original source token when source values are approximate or non-numeric.

Initial assumptions:

- `99+` means at least 99.
- Lipseys `ALLOCATED` and Davidsons `A` / `A*` mean the item is high-demand, short-supply, and not reliably available for ordinary online ordering.
- `Call`-like values mean quantity is unknown until the dealer contacts the distributor.

Default behavior under the initial `AvailabilityPolicy`:

- Exact positive quantities are `available` and exportable by default.
- Exact zero quantities are `out_of_stock` and not exportable by default.
- `99+` is `available`, uses `99` as the conservative lower-bound quantity, and carries an approximate-quantity warning.
- Other `X+` quantities should use `X` as the conservative lower-bound quantity unless `approximate_quantity_floor` is explicitly configured higher.
- Allocated values such as Lipseys `ALLOCATED` or Davidsons `A*` are `allocated`, use quantity `0` for default export decisions, and are not exportable unless `include_allocated` is enabled or a manual override exists.
- Unknown/call-for-availability values are `unknown`, use quantity `0`, and are not exportable unless `include_unknown_quantity` is enabled or a manual override exists.

GoDaddy supports tracked inventory quantity and backorder behavior, but current research has not found a CSV import field that safely creates an inquiry-only or "call for details" state. The MVP should therefore exclude allocated and unknown-quantity offers from website export by default instead of listing products that cannot be safely sold.

### `ShippingDetails`

Fields:

- `weight`
- `length`
- `width`
- `height`
- `disable_shipping`
- `free_shipping`
- `fixed_shipping_fee`

For Lipseys, prefer package dimensions when available for GoDaddy shipping fields, because GoDaddy's `WEIGHT`, `LENGTH`, `WIDTH`, and `HEIGHT` are shipping-oriented import columns.

For Davidsons, only weight is absent in the current sample, so dimensions may often remain blank.

### `ComplianceFlags`

Fields:

- `ffl_required`
- `sot_required`
- `nfa_item`
- `country_of_origin`

GoDaddy has no obvious dedicated FFL/SOT columns in the template. These flags should still be preserved so the exporter can add text to descriptions or future filters can exclude products.

Initial exporter behavior should add description notes for FFL, SOT, and NFA flags rather than excluding those products by default.

### `ProductMedia`

Fields:

- `image_url`
- `image_name`
- `image_source`

Lipseys provides `IMAGENAME` but not a full URL in the sample. Public site research found the reusable image host pattern:

```text
https://www.lipseyscloud.com/images/{IMAGENAME}?height=320&width=480&scale=canvas
```

The Lipseys adapter should build `image_url` from that pattern when `IMAGENAME` is present and not a missing-image placeholder. Current Davidsons samples do not contain image fields, so Davidsons offers should leave media fields blank unless a future feed/source provides image data.

Missing, blank, or broken image URLs should produce warnings only. They should not block otherwise valid product rows.

### `ValidationMessage`

Fields:

- `severity`: `info`, `warning`, or `error`
- `code`
- `message`
- `field`

Adapters should attach warnings for recoverable issues and errors for rows that cannot be exported.

## GoDaddy Column Coverage

| GoDaddy Column | Canonical Source | Initial Behavior |
| --- | --- | --- |
| `SKU` | `identity.canonical_sku` | Required |
| `EAN` | `identity.ean` | Optional blank |
| `UPC` | `identity.upc` | Required when available |
| `GTIN` | `identity.gtin` | Optional blank |
| `ISBN` | `identity.isbn` | Blank for current products |
| `TYPE` | export default | `PHYSICAL` |
| `NAME` | `details.name` | Required |
| `PRODUCT ID` | exporter import mode | Blank for new imports; required for update imports |
| `VARIANT GROUP ID` | future variant support | Blank initially |
| `SHORTCODE` | generated short code | Optional generated value |
| `MANUFACTURER` | `identity.manufacturer` | Optional |
| `MODEL NUMBER` | `identity.model_number` | Optional |
| `MSRP` | `pricing.msrp` | Optional |
| `BRAND` | `identity.brand` | Usually same as manufacturer |
| `STATUS` | `details.status` | `ACTIVE` by default |
| `PRICE` | `selected_offer.pricing.calculated_price` | Required |
| `SALE PRICE` | `selected_offer.pricing.sale_price` | Optional |
| `UNIT COST` | `selected_offer.pricing.unit_cost` | Optional but useful |
| `ALLOW CUSTOM PRICE` | export default | `false` |
| `ON-HAND QUANTITY` | `selected_offer.inventory.quantity` | Required |
| `TRACK INVENTORY` | `selected_offer.inventory.track_inventory` | `true` |
| `ALLOW BACKORDER` | `selected_offer.inventory.allow_backorder` | `false` initially |
| `DESCRIPTION` | `details.description` + attributes | Required |
| `DISABLE SHIPPING` | `shipping.disable_shipping` | `false` |
| `FREE SHIPPING` | `shipping.free_shipping` | `false` |
| `FIXED SHIPPING FEE` | `shipping.fixed_shipping_fee` | Optional blank |
| `WEIGHT` | `selected_offer.shipping.weight` | Optional |
| `LENGTH` | `selected_offer.shipping.length` | Optional |
| `WIDTH` | `selected_offer.shipping.width` | Optional |
| `HEIGHT` | `selected_offer.shipping.height` | Optional |
| `IMAGE URL` | `selected_offer.media.image_url` or product media | Optional; one image per CSV import |
| `OPTION 1-3 NAME/VALUE` | future variant/options | Blank initially |

## Description Strategy

Because GoDaddy lacks dedicated firearm/accessory attribute columns, the exporter should build a readable description from:

1. Source description.
2. Important attributes such as caliber, action, capacity, barrel length, finish, stock/grip, sights, magazine, and family.
3. Compliance notes such as FFL required or SOT required.

This feature only defines where those attributes live. The final text formatting belongs to the GoDaddy exporter feature.

## Source Selection

Source selection should be handled after feed adapters produce offers and before export adapters write rows.

Initial default policy from `RunConfiguration.source_selection` and `RunConfiguration.availability`:

1. Exclude offers that are not exportable by default, including zero quantity, allocated inventory, and unknown/call-for-availability inventory.
2. Exclude offers with blocking validation errors.
3. Prefer the highest estimated gross profit.
4. If tied, prefer higher quantity.
5. If tied, use configured distributor priority.

Estimated gross profit:

```text
selected_export_price - distributor_unit_cost
```

This policy should be configurable. SQLite should support saved defaults and product-level overrides such as always preferring a specific distributor for a UPC.

Source selection implementation is not part of this feature, but the canonical model must support it by keeping all source offers attached to a canonical product.

Dropshipping is out of scope for the MVP. Lipseys `CANDROPSHIP` and dropship-specific API fields should be preserved as source attributes if present, but they should not be used as a default listing requirement or fulfillment strategy.

## GoDaddy Export Modes

The GoDaddy exporter should support at least two modes:

- `new`: leave `PRODUCT ID` blank so GoDaddy can autogenerate it.
- `update`: populate `PRODUCT ID` from known GoDaddy product mappings.

The canonical model may still include an internal stable product key for dedupe, reporting, and repeatable processing. That internal key should not automatically be written to GoDaddy `PRODUCT ID` in new-import mode.

Default mode should be `new` through `RunConfiguration.export_mode`.

Update mode should require a mapping source. The preferred mapping source is local SQLite storage populated from a GoDaddy product export. If a mapping is unavailable, the exporter should not guess; it should produce a validation warning or skip that row, depending on the selected failure policy.

## Local Product Mapping

SQLite should be introduced in a later feature as the local product mapping and run-history store.

Responsibilities:

- Store generated export runs.
- Store run configuration snapshots.
- Store last-used operator configuration defaults.
- Store distributor/source identity fields.
- Store canonical SKU and UPC values.
- Store source offers seen per run.
- Store selected source offer per product per run.
- Store GoDaddy `PRODUCT ID` only after it has been learned from a GoDaddy export.
- Store user source-selection overrides.
- Support update-mode lookup by SKU first, UPC second.
- Support UI prompts when update mode needs a GoDaddy export sync.

The canonical model should include enough identity data to support this storage layer, but SQLite implementation is not part of this feature.

Proposed future SQLite tables:

```text
export_runs
  id
  created_at
  export_mode
  output_folder
  notes

product_mappings
  id
  canonical_sku
  upc
  distributor
  source_sku
  godaddy_product_id
  last_seen_export_run_id
  created_at
  updated_at

source_offers
  id
  export_run_id
  canonical_sku
  upc
  distributor
  source_sku
  unit_cost
  calculated_price
  quantity
  map_price
  is_selected

source_overrides
  id
  canonical_sku
  upc
  preferred_distributor
  preferred_source_sku
  created_at
  updated_at
```

The exact schema should be decided in the storage feature, not in the canonical model feature.

## GoDaddy Batching

GoDaddy Websites + Marketing Commerce currently documents a 100-product limit for bulk CSV upload. The exporter should support splitting large exports into 100-product files.

Proposed naming:

```text
godaddy-import-001.csv
godaddy-import-002.csv
godaddy-import-003.csv
```

## Operational Guardrails

The model should support these later UI/export guardrails:

- Show the source feed timestamp or run timestamp so the user understands that exported stock is a snapshot.
- Preserve offers that are excluded from export by default so the UI can report why they were not selected.
- Allow explicit review/override workflows for allocated or unknown-quantity offers, but keep those overrides separate from default selection.
- Tolerate missing images and broken public image URLs without blocking CSV export.
- Keep distributor images referenced by URL; do not download or commit image assets into the repository.
- Keep API/FTP retrieval outside the MVP until the operator has a working file-import path.

## Future Feature Notes

Recommended next features after this model is implemented:

- `0004-local-project-storage`: add SQLite storage for settings, export runs, and product mappings.
- `0005-source-aggregation-and-selection`: group source offers into canonical products and choose selected offers.
- `0006-godaddy-csv-exporter`: export GoDaddy CSV batches for new-import mode and define update-mode hooks.
- `0007-godaddy-export-sync`: import GoDaddy product exports and sync GoDaddy `PRODUCT ID` mappings into SQLite.
- `0008-update-mode-export`: enable update exports once mapping coverage and failure behavior are in place.
- `0009-distributor-feed-adapters`: implement dealer-downloaded Lipseys and Davidsons CSV adapters, including Lipseys image URL construction and conservative availability parsing.
- `0010-authenticated-feed-sources`: evaluate dealer-authorized API/FTP feed retrieval after the file-based workflow is working.
