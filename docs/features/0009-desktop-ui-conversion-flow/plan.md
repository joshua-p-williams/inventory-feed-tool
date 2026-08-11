# Plan

1. Update `DesktopAppState` to match `NewImportInput`.
2. Add state validation for the new input shape.
3. Add helpers to build `NewImportInput` and `RunConfiguration`.
4. Add workflow result formatting helpers.
5. Update Tkinter fields:
   - Lipseys CSV.
   - Davidsons inventory CSV.
   - Davidsons quantity CSV.
   - Output folder.
   - Markup percent.
   - Include image URLs.
6. Replace output save-as dialog with output folder selection.
7. Replace placeholder conversion with `run_new_import_workflow`.
8. Disable Convert during a run and re-enable it afterward.
9. Show summary, output files, warnings, and errors in the results area.
10. Add unit tests for app state and result formatting.
11. Update README and changelog.
12. Verify tests and package entry-point imports.

## Proposed Implementation Order

1. app state dataclass update
2. validation helpers
3. configuration/input builders
4. result formatter
5. app state tests
6. GUI field layout update
7. browse handlers
8. convert button wiring
9. smoke tests
10. docs updates

## Locked Decisions

- `0009` wires the desktop UI to `run_new_import_workflow`.
- The UI selects an output folder, not a single output CSV file.
- Lipseys and Davidsons are optional independent primary sources.
- Davidsons quantity CSV is optional and requires Davidsons inventory CSV.
- Update mode remains unavailable in the UI.
- Initial UI configuration includes markup percent and image URL inclusion.
- Default MAP, availability, and compliance behavior remain model defaults.
- SQLite persistence is not required for this feature.
- Generated files remain visible even when row-level errors occur.
- Keep testable conversion state and formatting outside Tkinter widget code.
- Store markup as text in desktop state and parse it during validation/configuration building.
- Use a scrollable read-only results widget instead of a wrapped label.
- For synchronous conversion, force pending UI updates before running the workflow.

## Review Points Before Coding

Resolved:

- Defer SQLite persistence for last-used settings and folders.
- Use synchronous conversion for this feature, with `update_idletasks()` before running the workflow and code structured so threading can be added later.

## Future Feature Queue

1. `0010-godaddy-export-sync`
2. `0011-update-mode-export`
3. `0012-authenticated-feed-sources`
