# Lipseys Distributor Feed Reference

Reviewed: 2026-08-08 and 2026-08-09

## Source URLs

- https://www.lipseys.com/faq
- https://www.lipseys.com/api-docs
- https://www.lipseys.com/catalog
- https://www.lipseys.com/itemdetail?itemno=HNH001
- https://www.lipseys.com/crm/dropshipaccessoryprogramguidelines
- https://www.lipseys.com/crm/dropshipfirearmsprogramguidelines

Local downloaded copies were kept in the parent project folder under `references/lipseys/` during research. Those downloaded pages are outside this repository; this repository keeps only this summary.

## Relevant Public Findings

- Lipseys `ALLOCATED` items are high-demand or short-supply and are not guaranteed to be available to a dealer.
- Adding items to a Lipseys cart does not reserve inventory; inventory is reserved only through checkout.
- Public site code indicates authenticated catalog feed endpoints exist, but authenticated API integration is outside the file-based MVP.
- Public image host pattern was identified:

```text
https://www.lipseyscloud.com/images/{IMAGENAME}?height=320&width=480&scale=canvas
```

- Public image fallback observed:

```text
https://www.lipseyscloud.com/images/li-missing-image.png
```

- Sample `IMAGENAME` values from local feed samples were verified to resolve as public images during research.
- Dropship documentation and fields exist, but dropshipping is out of scope for the MVP.

## Feed Columns Of Interest

Important Lipseys columns observed in local samples:

- Identity: `ITEMNO`, `UPC`, `MANUFACTURERMODELNO`
- Names/details: `DESCRIPTION1`, `DESCRIPTION2`, `MODEL`, `MANUFACTURER`, `TYPE`, `ITEMTYPE`, `ITEMGROUP`, `FAMILY`
- Attributes: `CALIBERGAUGE`, `ACTION`, `BARRELLENGTH`, `CAPACITY`, `FINISH`, `OVERALLLENGTH`, `SIGHTS`, `STOCKFRAMEGRIPS`, `MAGAZINE`, `CHAMBER`, `RATEOFTWIST`, `FRAME`, `GRIPTYPE`
- Pricing: `PRICE`, `CURRENTPRICE`, `MSRP`, `RETAILMAP`
- Availability: `QUANTITY`, `ALLOCATED`, `CANDROPSHIP`, `ONSALE`, `SPECIAL`
- Shipping/dimensions: `SHIPPINGWEIGHT`, `ITEMLENGTH`, `ITEMWIDTH`, `ITEMHEIGHT`, `PACKAGELENGTH`, `PACKAGEWIDTH`, `PACKAGEHEIGHT`
- Media: `IMAGENAME`
- Compliance: `FFLREQUIRED`, `SOTREQUIRED`

## Implementation Implications

- The Lipseys adapter should produce `SourceOffer` objects from dealer-downloaded CSV files.
- Use `ITEMNO` as source SKU.
- Use UPC-based canonical SKU when `UPC` is present.
- Use source-prefixed fallback SKU when UPC is missing.
- Prefer `CURRENTPRICE` for unit cost, falling back to `PRICE`.
- Use `RETAILMAP` as MAP when numeric and greater than zero.
- Parse `ALLOCATED` as allocated availability even if `QUANTITY` contains a number.
- Preserve `CANDROPSHIP` as metadata only.
- Build image URLs from `IMAGENAME` when present.
- Missing or broken image URLs should warn only.
- Extra columns should be preserved as source attributes where not mapped to first-class model fields.
