# Distributor Feed Adapters

## Purpose

Implement dealer-downloaded CSV feed adapters for the first supported distributors: Lipseys and Davidsons.

Each adapter should translate source-specific CSV rows into the shared `SourceOffer` model without writing target export files or selecting a winning offer.

## Scope

- Add a feed adapter module structure.
- Parse Lipseys catalog-style CSV files into `SourceOffer` objects.
- Parse Davidsons inventory CSV files into `SourceOffer` objects.
- Optionally merge Davidsons warehouse quantity CSV data into Davidsons inventory rows.
- Support running either distributor independently; both distributors are not required in the same run.
- Use shared parsing helpers for money, booleans, optional text, and availability tokens.
- Use shared configurable pricing helpers through `RunConfiguration.pricing`.
- Build Lipseys image URLs from `IMAGENAME`.
- Preserve extra source fields in `attributes`.
- Attach row-level warnings without crashing the whole feed.
- Add tests using sanitized, hand-written CSV fixtures.

## Out of Scope

- Grouping duplicate products across distributors.
- Choosing selected offers.
- Writing GoDaddy CSV files.
- Syncing GoDaddy product exports.
- Update-mode export behavior.
- Authenticated distributor API or FTP retrieval.
- Desktop UI wiring.

Those remain separate features.

## Success Criteria

- Lipseys CSV rows can be parsed into `SourceOffer` objects.
- Davidsons inventory CSV rows can be parsed into `SourceOffer` objects.
- Davidsons warehouse quantity CSV data can be used when provided.
- Lipseys-only parsing works.
- Davidsons-only parsing works.
- Davidsons quantity CSV cannot be parsed by itself without the Davidsons inventory CSV.
- Feed adapters do not hardcode pricing markup or MAP behavior.
- Allocated, unknown, and approximate quantities are represented consistently with the canonical model.
- Lipseys image URLs are populated when `IMAGENAME` is present.
- Davidsons image URLs remain blank unless a future source provides image fields.
- Missing required row fields create validation messages and skip only affected rows.
- Extra source columns are preserved as key/value attributes.
- Tests do not depend on real distributor feed files.
