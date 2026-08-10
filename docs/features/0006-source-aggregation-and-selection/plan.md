# Plan

1. Add `aggregation.py`.
2. Add `SourceSelectionOverride`.
3. Implement grouping by canonical SKU.
4. Implement exportable candidate filtering.
5. Implement override matching.
6. Implement gross-profit selection.
7. Implement quantity selection.
8. Implement distributor-priority selection.
9. Implement deterministic tie-breakers.
10. Implement conflict detection.
11. Build representative `CanonicalProduct` identity/details from the selected offer.
12. Add focused unit tests with hand-built offers.
13. Update README and changelog.

## Proposed Implementation Order

1. `SourceSelectionOverride`
2. source display/tie-break helpers
3. distributor priority helper
4. grouping helper
5. candidate filtering
6. override selection
7. strategy scoring
8. representative identity/details helpers
9. conflict detection
10. public `AggregationResult` and `aggregate_source_offers`
11. tests
12. README and changelog updates

## Locked Decisions

- Aggregation is a pure model-layer operation.
- Aggregation does not parse CSV files.
- Aggregation does not write target export files.
- Aggregation does not open SQLite or depend on `LocalStore`.
- Group source offers by `identity.canonical_sku`.
- Preserve every source offer on each `CanonicalProduct`.
- Default selection considers only exportable offers.
- If no exportable offer exists, drop that product group from returned products and attach a warning to `AggregationResult.messages`.
- `aggregate_source_offers` returns `AggregationResult`, not a bare product tuple.
- Aggregation overrides remain target-neutral. Storage may scope overrides by target system, but orchestration is responsible for loading relevant target-system overrides before calling aggregation.
- Manual overrides are accepted as input but do not select non-exportable offers in this feature.
- The default strategy is `gross_profit`.
- Tie-breakers must be deterministic.
- Conflict messages are warnings in the first implementation.
- MAP conflicts warn only when two or more nonblank MAP values differ.
- Do not add fuzzy matching in this feature.

## Review Points Before Coding

No open review points remain for this feature.

## Future Feature Queue

1. `0007-godaddy-csv-exporter`
2. `0008-godaddy-export-sync`
3. `0009-update-mode-export`
4. `0010-authenticated-feed-sources`
