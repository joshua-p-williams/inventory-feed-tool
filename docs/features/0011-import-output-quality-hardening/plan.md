# Plan

## Implementation Steps

1. Review current Davidsons UPC parsing tests and GoDaddy exporter money tests.
2. Add failing regression tests for invalid Davidsons UPC export behavior.
3. Add failing regression tests for fixed two-decimal GoDaddy money formatting.
4. Add failing regression tests for Davidsons image URL construction.
5. Update Davidsons adapter normalization so invalid UPC values do not populate `ProductIdentity.upc`.
6. Update Davidsons adapter media enrichment so safe item numbers produce Cloudinary image URLs.
7. Update GoDaddy exporter `_money()` to keep two decimal places.
8. Run the full test suite.
9. Regenerate or re-analyze output against the real result folder after implementation.
10. Update this feature's research notes with post-fix findings.

## Preferred Code Changes

### Davidsons Adapter

Current:

```python
canonical_sku = _canonical_sku(upc, source_sku, row_number, messages)
...
identity=ProductIdentity(
    canonical_sku=canonical_sku,
    upc=upc,
)
```

Target:

```python
canonical_sku, normalized_upc = _identity_values(upc, source_sku, row_number, messages)
...
identity=ProductIdentity(
    canonical_sku=canonical_sku,
    upc=normalized_upc,
)
```

The helper should return `None` for missing or invalid UPC values.

### GoDaddy Exporter

Current:

```python
return _strip_decimal(rounded)
```

Target:

```python
return format(rounded, ".2f")
```

Keep `_decimal()` unchanged.

### Davidsons Images

Add a deterministic helper that constructs image URLs from safe `Item #` values:

```text
https://res.cloudinary.com/davidsons-inc/image/upload/media/catalog/product/<first>/<second>/<Item #>.jpg
```

Do not perform live HTTP checks during normal conversion.

Do not construct URLs for item numbers with unsafe URL/path characters such as `/`, `\`, `?`, `#`, or whitespace.

## Validation Commands

Run:

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m compileall src tests
git diff --check
```

After regenerating output, use a small analysis script or helper to confirm:

```text
UPC=## count: 0
money fields not two decimals: 0
Davidsons image URL count: increased from previous run
duplicate SKU count: 0
header mismatch count: 0
```

## Documentation Updates

- Mark task checklist as complete.
- Update `CHANGELOG.md`.
- Update `README.md` only if user-facing behavior needs explicit mention.
- Keep roadmap next path pointed at GoDaddy export sync after this hardening feature.
