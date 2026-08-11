# Research

## Prior Feature Decisions

From `0002-desktop-app-packaging-shell`:

- The desktop app uses Tkinter to avoid adding GUI dependencies.
- The app must remain packageable as a Windows executable.
- The UI shell currently exists as a basic file-picker form.

From `0005-distributor-feed-adapters`:

- Lipseys CSV can run independently.
- Davidsons inventory CSV can run independently.
- Davidsons quantity CSV is optional, but only valid with Davidsons inventory CSV.
- Davidsons quantity CSV alone cannot produce source offers.

From `0008-new-import-workflow`:

- The UI should call `run_new_import_workflow`.
- The workflow expects `NewImportInput`.
- The workflow uses an output directory because GoDaddy CSV export can create multiple batch files.
- The workflow preserves warnings/errors and still reports generated files for partial success.
- Update mode is not supported yet.

## Current UI Shape

Current app state:

```python
DesktopAppState(
    davidsons_file: Path | None,
    lipseys_file: Path | None,
    output_file: Path | None,
)
```

Current UI:

- One Davidsons picker.
- One Lipseys picker.
- One GoDaddy output CSV save dialog.
- Placeholder convert message.

This no longer matches the implemented workflow. `0009` should update the shape to:

```python
DesktopAppState(
    lipseys_csv: Path | None,
    davidsons_inventory_csv: Path | None,
    davidsons_quantity_csv: Path | None,
    output_dir: Path | None,
    markup_percent_text: str,
    include_image_urls: bool,
)
```

## UI Implications

The output control should select a folder, not a file.

Reason:

- GoDaddy import batches are capped at 100 products.
- `export_godaddy_csv` may generate multiple files.
- A single save-as CSV path is misleading and incompatible with batching.

The Davidsons control should be split into two rows:

- Davidsons inventory CSV.
- Davidsons quantity CSV.

The quantity row should be visually optional and should not be treated as a primary source.

## Initial Run Options

Configuration needs to be visible enough to support the decisions already built into the model without becoming a full settings screen.

Initial controls:

- Markup percent numeric entry.
- Include image URLs checkbox.

Defaults:

- Markup percent: current `PricingProfile` default.
- Include image URLs: current `ImagePolicy` default.
- Export mode: always new import in this feature.
- MAP handling: default model behavior, respect MAP.
- Availability: default model behavior, conservative exportable rows only.
- Compliance: default model behavior, description notes.

These controls keep the first UI practical while leaving full configuration management for a later feature.

The state model should store markup as text, not `Decimal`, because the value originates in a Tkinter entry. Validation should parse the text into `Decimal` and report invalid or negative values without raising a widget-handler exception.

## Result Display

The UI should show:

- Whether the run completed, completed with warnings/errors, or failed validation before export.
- Source rows seen.
- Source offers parsed.
- Product groups found.
- Product groups dropped.
- Products exported.
- Products skipped.
- Output files written.
- Warning/error messages.

Generated file paths should remain visible even when some source rows had errors and the workflow returns `has_errors = True`.

The current `ttk.Label` status area is not enough for real parser/export messages. Use a scrollable read-only text area for results so long warning lists and multiple output file paths remain inspectable.

## Testing Implications

Tkinter widgets are hard to test reliably in headless CI. Keep testable logic outside widget code:

- state validation
- `RunConfiguration` construction
- `NewImportInput` construction
- result summary formatting

The Tkinter class can stay thin and use those helpers.

## Open Questions

No blocking questions remain.

Resolved review points:

- Defer last-used folder/settings persistence to a later preferences or run-history feature.
