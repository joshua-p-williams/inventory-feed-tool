# Architecture

## Design Direction

Keep the desktop UI thin and move workflow-facing state logic into testable helpers.

Proposed module updates:

```text
src/inventory_feed_tool/
  app_state.py
  gui.py
```

No new GUI framework should be introduced. Continue using Tkinter and `ttk`.

## State Model

Update `DesktopAppState` to represent the workflow input shape:

```python
@dataclass(frozen=True)
class DesktopAppState:
    lipseys_csv: Path | None = None
    davidsons_inventory_csv: Path | None = None
    davidsons_quantity_csv: Path | None = None
    output_dir: Path | None = None
    markup_percent_text: str = "25"
    include_image_urls: bool = True
```

Helper methods should build:

```python
def to_new_import_input(self) -> NewImportInput:
    ...

def to_run_configuration(self) -> RunConfiguration:
    ...
```

Validation should cover:

- at least one primary source
- Davidsons quantity requires Davidsons inventory
- provided source paths exist and are files
- output folder is selected
- output folder path is not an existing file
- markup percent parses and is nonnegative

## UI Layout

Use a compact utility layout rather than a landing-page style.

Sections:

1. Inputs
   - Lipseys CSV
   - Davidsons inventory CSV
   - Davidsons quantity CSV
   - Output folder
2. Options
   - Markup percent
   - Include image URLs
3. Results
   - summary counts
   - output files
   - messages
4. Actions
   - Convert
   - Close

The current UI uses labels, entries, and Browse buttons. Continue that pattern for consistency.

The results section should use a scrollable read-only text widget instead of a wrapped label. Conversion messages can be long, and generated output files must remain visible even when warnings/errors are present.

## Conversion Flow

When Convert is clicked:

1. Collect widget values into `DesktopAppState`.
2. Validate state locally.
3. If validation fails, show messages and do not call workflow.
4. Disable Convert button.
5. Set status to a running message.
6. Force pending UI updates with `update_idletasks()`.
7. Run `run_new_import_workflow`.
8. Format `NewImportWorkflowResult` into user-readable output.
9. Re-enable Convert button.

Because the first workflows should be small local CSV runs, synchronous execution is acceptable for `0009`. The code should keep the conversion call isolated so a later progress/threading feature can move it off the UI thread if needed.

## Result Formatting

Add UI-independent formatting helpers:

```python
def format_workflow_result(result: NewImportWorkflowResult) -> str:
    ...
```

Suggested format:

```text
Completed with warnings.

Rows seen: 250
Offers parsed: 240
Product groups: 230
Product groups dropped: 5
Products exported: 225
Products skipped: 0

Output files:
C:\...\godaddy-import-001.csv
C:\...\godaddy-import-002.csv

Messages:
WARNING lipseys_missing_upc: ...
ERROR lipseys_missing_unit_cost: ...
```

If validation fails before workflow execution, show validation messages without a success summary.

## Error Handling

Expected user-correctable issues should be shown in the status/results area, not as stack traces.

Use message boxes sparingly:

- validation failure: warning message box plus details in results area
- completed run: information message box may be used, but results area is the primary record
- unexpected exception: error message box plus concise status text

Generated output file paths should be visible in the results area even when row-level errors occur.

## Storage Boundary

Do not require SQLite for `0009`.

`LocalStore` may later provide:

- default run configuration
- last-used folders
- run history
- source-selection overrides

For this feature, keep the UI deterministic and backed by current widget values.

## Tests

Avoid launching a real Tkinter main loop in unit tests.

Coverage should include:

- state allows Lipseys-only input
- state allows Davidsons inventory-only input
- state allows Davidsons inventory plus quantity
- state rejects Davidsons quantity-only input
- state rejects output path that is an existing file
- state rejects invalid/negative markup
- state builds `NewImportInput`
- state builds `RunConfiguration` with markup percent and image option
- result formatter includes output files on partial success
- result formatter includes validation errors

Existing CLI and workflow tests continue to cover actual conversion behavior.
