# Architecture

## Modules

```text
src/inventory_feed_tool/
  app_state.py   UI-independent state and validation helpers
  gui.py         Tkinter desktop application
  gui_app.py     GUI entry point
```

The desktop UI should not contain ETL business logic. It should collect file paths and options, call shared conversion services, then render status messages and warnings.

For this feature, the conversion service does not exist yet. The shell exposes the workflow and returns a clear "not implemented" message when conversion is requested.

## Entry Points

The CLI remains available as:

```bash
inventory-feed-tool
```

The desktop UI is available as:

```bash
inventory-feed-tool-gui
```

The PyInstaller build targets the GUI entry point.

## Test Strategy

Tests should cover UI-independent state and validation helpers. Tkinter window creation is not tested in CI because headless Linux runners may not have a display server.
