# Architecture

## Design Direction

Add a pure aggregation and source-selection module that receives `SourceOffer` objects and returns selected `CanonicalProduct` objects plus aggregation messages.

Proposed module layout:

```text
src/inventory_feed_tool/
  aggregation.py
```

The module should not read files, write exports, or open SQLite connections.

## Core API

Proposed public function:

```python
@dataclass(frozen=True)
class AggregationResult:
    products: tuple[CanonicalProduct, ...]
    messages: tuple[ValidationMessage, ...] = ()
    source_offer_count: int = 0
    product_group_count: int = 0
    product_groups_dropped: int = 0

def aggregate_source_offers(
    offers: Iterable[SourceOffer],
    configuration: RunConfiguration | None = None,
    overrides: Iterable[SourceSelectionOverride] = (),
) -> AggregationResult:
    ...
```

Proposed helper dataclass:

```python
@dataclass(frozen=True)
class SourceSelectionOverride:
    canonical_sku: str
    preferred_distributor: str | None = None
    preferred_source_sku: str | None = None
```

The existing storage layer has its own `SourceOverride` row type that includes target-system scope. The aggregation override type should stay target-neutral, small, and model-oriented. Later orchestration should load the relevant target-system overrides from storage and translate those rows into this type before calling aggregation.

## Grouping

Group offers by `offer.identity.canonical_sku`.

Ordering should be deterministic:

1. Sort product groups by canonical SKU.
2. Preserve offers inside each product in a deterministic source order.
3. Use stable tie-breakers when scores are equal.

For each group with at least one exportable candidate:

- Select a representative `ProductIdentity`.
- Select representative `ProductDetails`.
- Preserve all offers.
- Attach conflict messages.
- Choose `selected_offer`.

For groups with no exportable candidates:

- Do not return a `CanonicalProduct`.
- Increment `product_groups_dropped`.
- Attach a run-level warning such as `no_exportable_offer`.

## Representative Product Fields

The canonical product should use product-level values from the selected offer.

This keeps exported product-level fields aligned with the selected offer while still preserving all alternate offers.

Representative identity:

- `canonical_sku`: group key
- `upc`: first nonblank UPC, preferring the selected offer
- `manufacturer`: selected offer value, fallback first nonblank
- `brand`: selected offer value, fallback first nonblank
- `model_number`: selected offer value, fallback first nonblank
- `model_name`: selected offer value, fallback first nonblank

Representative details:

- `name`: selected offer value, fallback first offer
- `description`: selected offer value, fallback first offer
- `product_type`: selected offer value, fallback `PHYSICAL`
- `category`: selected offer value, fallback first nonblank
- `family`: selected offer value, fallback first nonblank
- `status`: selected offer value, fallback `ACTIVE`

## Candidate Filtering

Automatic selection should begin with exportable candidates:

```text
offer.inventory.is_exportable_by_default == true
```

The current feed adapters skip rows with blocking parse errors, so no separate blocking-error field exists on `SourceOffer`.

If no exportable candidates exist:

- do not return a `CanonicalProduct` for that group
- increment `AggregationResult.product_groups_dropped`
- attach a run-level warning such as `no_exportable_offer`

Do not silently select allocated, unknown, or zero-quantity offers under default configuration. Do not silently drop them either; report dropped groups through `AggregationResult.messages`.

## Overrides

If `configuration.source_selection.allow_manual_overrides` is true and a matching override exists:

1. Match by canonical SKU.
2. Search exportable candidates for matching distributor and optional source SKU.
3. If found, select that offer.
4. If not found, attach a warning and continue with automatic selection.

Initial override matching rules:

- `preferred_distributor` alone can select the first matching exportable offer for that distributor.
- `preferred_distributor` plus `preferred_source_sku` selects the exact source offer.
- `preferred_source_sku` without distributor can be supported, but distributor plus SKU is preferred because source SKUs are not globally unique.

Overrides should not select non-exportable offers in this feature. If an override only matches non-exportable offers, the group should follow normal fallback selection or be dropped if no exportable candidate exists. A later manual-review workflow can add an explicit unsafe override mode if needed.

## Selection Strategies

Use `RunConfiguration.source_selection.strategy`.

### Gross Profit

Default strategy.

Score:

```text
offer.pricing.calculated_price - offer.pricing.unit_cost
```

Higher is better.

Tie-breakers:

1. higher inventory quantity
2. configured distributor priority
3. lower source display name

### Quantity

Score:

```text
offer.inventory.quantity
```

Higher is better.

Tie-breakers:

1. higher gross profit
2. configured distributor priority
3. lower source display name

### Distributor Priority

Use `configuration.source_selection.preferred_distributors`.

Lower index is better. Distributors not present in the configured priority list sort after configured distributors.

Tie-breakers:

1. higher gross profit
2. higher inventory quantity
3. lower source display name

## Distributor Priority Matching

Distributor identifiers should be compared case-insensitively after trimming whitespace.

Examples:

- `lipseys`
- `davidsons`

The code should not hardcode these as the only possible distributor names. Unknown distributors should still sort deterministically.

## Conflict Detection

Attach `ConflictMessage.warning` entries to the `CanonicalProduct` when nonblank values differ across offers for these fields:

- `identity.manufacturer`
- `identity.brand`
- `identity.model_number`
- `identity.model_name`
- `details.name`
- `details.category`
- `pricing.map_price`

Conflict comparison should normalize strings by trimming whitespace and using case-insensitive comparison. Do not fuzzy-match names in this feature.

MAP conflicts should warn only when two or more nonblank MAP values differ. A source with blank MAP and another source with nonblank MAP is not a conflict by itself.

Conflict messages should include the field and involved source display names.

## Validation Messages

Use `ValidationMessage.warning` on canonical products for selection warnings:

- stale or unmatched override
- override disabled by configuration

Use `ValidationMessage.warning` on the aggregation result for dropped groups:

- no exportable candidate

Use `ConflictMessage.warning` for cross-offer product conflicts.

## Storage Boundary

The aggregation module should not import `LocalStore`.

Later orchestration can:

1. load source offers from current feed adapter results
2. load saved source overrides from SQLite
3. translate storage rows into `SourceSelectionOverride`
4. call `aggregate_source_offers`
5. store source offer snapshots and selected-offer flags

## Tests

Tests should create `SourceOffer` objects directly, without CSV fixtures.

Coverage should include:

- grouping by canonical SKU
- selected offer by gross profit
- selected offer by quantity
- selected offer by distributor priority
- tie-break determinism
- non-exportable offers excluded by default
- dropped group and warning when every offer is non-exportable
- manual override success
- stale manual override warning and fallback
- manual overrides disabled
- conflict detection
- representative fields prefer selected offer
