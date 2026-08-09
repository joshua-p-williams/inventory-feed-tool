# Canonical Inventory Model

## Purpose

Define the shared internal product and source-offer model used between distributor feed adapters and website export adapters.

The model must be generic enough to support multiple distributors and export targets, but it must satisfy the GoDaddy product import CSV template as the minimum required output contract.

## Scope

- Define canonical product fields.
- Define distributor source-offer fields.
- Define how multiple distributor offers are grouped into one sellable product.
- Define conflict reporting and source-selection concepts.
- Define source metadata needed for traceability and duplicate handling.
- Define run configuration and policy objects that control pricing, availability filtering, source selection, image handling, compliance behavior, and export mode.
- Define pricing fields and the configurable MAP-aware pricing strategy.
- Define availability fields that distinguish exact stock from allocated, approximate, or unknown stock.
- Define image metadata needed to produce GoDaddy image URLs when a distributor provides reusable public image names.
- Define validation/reporting concepts used by adapters and exporters.
- Define how firearm/accessory details should be preserved when the export format lacks dedicated columns.
- Add tests for the model and pricing behavior when implemented.

## Out of Scope

- Parsing Davidsons feeds.
- Parsing Lipseys feeds.
- Writing GoDaddy CSV files.
- End-to-end conversion.
- Desktop UI conversion wiring.
- Dropship workflow support.

Those will be handled as separate features after the model is agreed.

## Success Criteria

- A future feed adapter can convert one source row into a source offer without knowing GoDaddy-specific CSV column order.
- A future aggregation step can group source offers into canonical products by UPC or another stable identity.
- Pricing, availability filtering, source selection, image behavior, compliance behavior, and export mode can be controlled through explicit run configuration instead of hardcoded adapter behavior.
- A future GoDaddy exporter can populate every required GoDaddy template column from a canonical product and its selected source offer.
- Product details that do not have GoDaddy columns can still be carried as attributes and rendered into the product description.
- Multiple distributor offers for the same UPC can be preserved, compared, and resolved without data loss.
- Offers with allocated or uncertain availability can be preserved for review without being automatically selected for website export.
- Invalid or incomplete source records can produce warnings without crashing the whole conversion.
