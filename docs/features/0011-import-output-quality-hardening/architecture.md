# Architecture

## Design Direction

Keep this feature as a targeted hardening pass.

The ETL model, aggregation strategy, workflow orchestration, UI, and storage layers do not need broad changes. The discovered issues belong at three boundaries:

1. Source adapter normalization for invalid Davidsons UPC values.
2. GoDaddy exporter formatting for money fields.
3. Source adapter media enrichment for Davidsons image URLs.

## Invalid UPC Handling

### Current Shape

Davidsons parsing currently:

1. reads source UPC text from `UPC Code`
2. calculates `canonical_sku` by calling `_canonical_sku(upc, source_sku, ...)`
3. returns a fallback SKU when UPC is missing or invalid
4. passes the original source `upc` text into `ProductIdentity.upc`

This lets invalid values such as `##` leak into the target CSV.

### Proposed Shape

Introduce a source-adapter helper that normalizes UPC identity fields and fallback SKU decisions together.

One simple option:

```python
@dataclass(frozen=True)
class IdentifierResult:
    canonical_sku: str
    upc: str | None
    messages: tuple[ValidationMessage, ...] = ()
```

For this narrow feature, a private Davidsons helper is enough:

```python
def _identity_values(
    upc: str | None,
    source_sku: str,
    row_number: int,
) -> tuple[str, str | None, tuple[ValidationMessage, ...]]:
    ...
```

Behavior:

- valid UPC:
  - `canonical_sku = UPC-<digits>`
  - `upc = <normalized valid UPC>`
- missing UPC:
  - warning
  - `canonical_sku = DAV-<source sku>`
  - `upc = None`
- invalid UPC:
  - warning
  - `canonical_sku = DAV-<source sku>`
  - `upc = None`

This keeps the exporter target-neutral: the source adapter produces a clean middle model and the exporter simply writes the model.

### UPC Normalization

Use the existing `canonical_sku_from_upc()` behavior for canonical SKU creation.

For the exported UPC value, preserve only a valid UPC-like digit string. At minimum:

- strip whitespace
- remove non-digit separators only if the existing parser already tolerates them
- reject values with no digits
- reject obvious placeholders such as `##`

The initial implementation can mirror the current canonical SKU validation rule: if `canonical_sku_from_upc()` raises, the exported UPC should be blank.

## Money Formatting

### Current Shape

`_money()` in the GoDaddy exporter:

```python
rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
return _strip_decimal(rounded)
```

This produces valid but inconsistent values:

- `794`
- `992.5`
- `137.49`

### Proposed Shape

Change only `_money()`:

```python
def _money(value: Decimal | None) -> str:
    if value is None:
        return ""
    rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return format(rounded, ".2f")
```

Leave `_decimal()` unchanged for weight and dimensions because those are not money fields and may not need fixed two-decimal formatting.

## Davidsons Image URL Construction

### Current Shape

The Davidsons adapter currently emits:

```python
media=ProductMedia()
```

This leaves `IMAGE URL` blank for selected Davidsons offers.

### Proposed Shape

Add a small deterministic helper in the Davidsons adapter:

```python
DAVIDSONS_IMAGE_BASE_URL = (
    "https://res.cloudinary.com/davidsons-inc/image/upload/media/catalog/product"
)

def _image_url(source_sku: str) -> str | None:
    ...
```

For item numbers with at least two safe characters, construct:

```text
{base}/{first-char-lower}/{second-char-lower}/{item-number}.jpg
```

Examples:

```text
16412        -> .../1/6/16412.jpg
GERMMP40925  -> .../g/e/GERMMP40925.jpg
5PS1545A23   -> .../5/p/5PS1545A23.jpg
```

Populate:

```python
ProductMedia(
    image_url=_image_url(source_sku),
    image_name=f"{source_sku}.jpg",
    image_source="davidsons_cloudinary_item_number",
)
```

### URL Safety

Some item numbers contain characters that may not be safe as a Cloudinary public ID filename. The first implementation should be conservative:

- allow alphanumeric characters, hyphen, underscore, and dot
- do not construct URLs for item numbers with slash, backslash, whitespace, query-string characters, or fragments
- preserve blank image URL for unsafe item numbers

This avoids generating obviously broken GoDaddy import image URLs.

### Validation

Do not make live HTTP validation part of the default conversion. It would slow down large feeds and introduce network failure into a file-based workflow.

Future validation can be controlled by `ImagePolicy.validate_image_urls`, but the first implementation should be deterministic and offline.

### Warnings

Avoid per-row warnings for every unconstructed Davidsons image URL. This would flood logs and UI summaries. If warnings are added later, they should be summarized or emitted only when validation is explicitly enabled.

## Output Analysis Helper

The manual audit was useful enough to capture as executable project knowledge.

Potential helper:

```text
src/inventory_feed_tool/output_quality.py
```

Possible API:

```python
@dataclass(frozen=True)
class CsvOutputQualityReport:
    file_count: int
    row_count: int
    header_mismatch_count: int
    duplicate_sku_count: int
    invalid_upc_values: tuple[str, ...]
    money_not_two_decimal_count: int
```

This is useful but not strictly required for the first fix. If added, it should remain independent of Tkinter and be easy to use from tests or a future CLI command.

## Testing

Add focused tests rather than broad snapshot tests:

- Davidsons adapter:
  - invalid UPC emits a warning
  - invalid UPC uses fallback canonical SKU
  - invalid UPC results in `identity.upc is None`
- GoDaddy exporter:
  - money fields are fixed to two decimals
  - blank money values remain blank
- End-to-end workflow or exporter regression:
  - product with fallback SKU and blank UPC exports without `##`
- Davidsons adapter:
  - safe item number produces expected Cloudinary image URL
  - unsafe item number leaves image URL blank
  - image metadata records the source

If an output-quality helper is added, test it with tiny generated CSV fixtures rather than full distributor sample files.

## Risks

- If GoDaddy accepts integer money values, fixed two-decimal formatting is still safe and more predictable.
- If an invalid Davidsons UPC string contains meaningful distributor-specific data, blanking it in `UPC` is still safer than exporting it as a universal product code.
- Existing tests may assert stripped money output; update those expectations intentionally.

## Deferred

- Live Davidsons image URL validation.
- GoDaddy import dry-run automation.
- Category enrichment.
- Product review queues for dropped groups.
