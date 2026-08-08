# Research

## UI Toolkit

Tkinter is the initial UI toolkit choice.

Reasons:

- It ships with standard Python distributions.
- It works with PyInstaller.
- It is adequate for a focused utility with file pickers, status messages, and a convert button.
- It avoids runtime dependency weight while the ETL engine is still being shaped.

## Packaging

PyInstaller is the first packaging target.

Expected deliverable shape:

```text
dist/
  InventoryFeedTool/
    InventoryFeedTool.exe
    _internal/
```

A one-folder build is preferred initially because it is easier to debug than a one-file executable and tends to trigger fewer packaging surprises.

## CI

The repository should keep normal tests separate from packaging. Packaging can run manually through `workflow_dispatch` or on version tags after the release process is defined.

## Open Questions

- Should release builds be one-folder zips or one-file executables?
- Will Jeremiah prefer a portable zip or a Windows installer?
- Should code signing be added later to reduce antivirus warnings?
