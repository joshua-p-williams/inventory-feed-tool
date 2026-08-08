# Architecture

## Shape

The initial skeleton separates project concerns without adding application complexity.

```text
src/inventory_feed_tool/
  __init__.py
  __main__.py
  cli.py
```

The CLI is intentionally thin. Future features should keep parsing, normalization, pricing, validation, and exporting in separate modules that can be used by both the CLI and desktop UI.

## Packaging Considerations

The eventual desktop executable should call into the same ETL services as the CLI. That avoids duplicating business logic between interfaces and makes automated testing easier.

The current skeleton avoids runtime third-party dependencies. Future dependencies should be evaluated for license compatibility, package size, and PyInstaller behavior before adoption.
