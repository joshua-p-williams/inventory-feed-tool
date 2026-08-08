# Desktop App Packaging Shell

## Purpose

Prove that Inventory Feed Tool can run as a simple local desktop application and has a clear path to a Windows executable deliverable.

## Scope

- Add a basic Tkinter desktop app shell.
- Add a GUI entry point that can be launched from Python.
- Add packaging metadata and scripts for a PyInstaller-based Windows build.
- Add GitHub Actions workflow support for a Windows executable artifact.
- Add tests that verify the GUI model without requiring a display server.

## Out of Scope

- Distributor feed parsing.
- GoDaddy CSV export.
- Real conversion behavior.
- Installer creation or code signing.

Those will be handled as separate features.
