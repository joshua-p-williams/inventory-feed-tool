# Desktop UI Conversion Flow

## Purpose

Connect the desktop app to the new-import workflow so a non-technical user can run a file-based conversion without using the command line.

This feature turns the current Tkinter shell from a placeholder into the first usable desktop workflow: select distributor files, choose an output folder, run conversion, and review generated GoDaddy CSV batches plus warnings.

## Scope

- Replace placeholder conversion behavior with `run_new_import_workflow`.
- Update desktop state from single Davidsons file to:
  - Lipseys CSV.
  - Davidsons inventory CSV.
  - Davidsons quantity CSV, optional.
  - Output folder.
- Use an output folder picker instead of a single output CSV save dialog.
- Keep Lipseys and Davidsons inputs independent; do not require both distributors.
- Reject Davidsons quantity CSV without Davidsons inventory CSV.
- Display a clear run summary after conversion.
- Display generated output file paths.
- Display validation warnings and errors in a scrollable results area.
- Add basic run options for pricing markup and image URL inclusion.
- Keep update mode out of the UI for now.
- Keep the UI generic and avoid customer/operator-specific names.
- Add tests for UI-independent desktop state validation and summary formatting.

## Out Of Scope

- GoDaddy product export import.
- GoDaddy update-mode export.
- SQLite-backed run history or source-offer snapshots.
- Editing source-selection overrides.
- Product review queue.
- Authenticated distributor feed retrieval.
- Full settings/preferences management.
- Advanced pricing profiles beyond the initial markup and image controls.
- Automatic opening of generated CSV files or output folders.

Those remain separate features.

## Success Criteria

- User can select a Lipseys CSV and output folder, then run conversion.
- User can select a Davidsons inventory CSV and output folder, then run conversion.
- User can optionally select a Davidsons quantity CSV when Davidsons inventory is selected.
- User can select both Lipseys and Davidsons files in one run.
- UI prevents or clearly reports missing sources, missing output folder, missing files, and Davidsons quantity-only input.
- UI passes a `RunConfiguration` to the workflow based on visible controls.
- UI shows source rows seen, source offers parsed, product groups, products exported, products skipped, and output files.
- UI shows warnings/errors in a scrollable read-only results area without hiding generated file paths when partial exports succeed.
- Convert button is disabled while conversion is running.
- The app remains packageable with the existing Windows PyInstaller workflow.
- Tests cover the UI-independent state/result formatting logic without launching Tkinter.
