# Davidsons Distributor Feed Reference

Reviewed: 2026-08-08 and 2026-08-09

## Source URLs

- https://legacy.davidsonsinc.com/login/default.aspx?pg=faq

Local downloaded copies were kept in the parent project folder under `references/davidsons/` during research. Those downloaded pages are outside this repository; this repository keeps only this summary.

## Relevant Public Findings

- Davidsons inventory downloads are available to logged-in dealers.
- Davidsons may also provide FTP inventory downloads.
- Manufacturer MAP information is available through Davidsons dealer resources.
- Davidsons does not backorder items.
- Cart items are not secured until checkout is completed.
- `A` / allocated means demand exceeds supply and the item is unavailable to order online.
- `Call` means quantity requires account-executive confirmation.
- GalleryofGuns/Davidsons public product pages can expose full-color product images.
- Public image results showed Davidsons product media hosted through Cloudinary under `res.cloudinary.com/davidsons-inc`.

## Feed Columns Of Interest

Important Davidsons inventory columns observed in local samples:

- Identity: `Item #`, `UPC Code`
- Names/details: `Item Description`, `Manufacturer`, `Gun Type`, `Model Series`
- Attributes: `Caliber`, `Action`, `Capacity`, `Finish`, `Stock`, `Sights`, `Barrel Length`, `Overall Length`, `Features`
- Pricing: `MSP`, `Retail Price`, `Dealer Price`, `Sale Price`, `Sale Ends`
- Availability: `Quantity`

Important Davidsons quantity columns observed in local samples:

- Join fields: `Item_Number`, `UPC_Code`
- Warehouse quantities: `Quantity_NC`, `Quantity_AZ`

## Implementation Implications

- The Davidsons adapter should produce `SourceOffer` objects from dealer-downloaded CSV files.
- Davidsons inventory CSV is required for Davidsons parsing.
- Davidsons quantity CSV is optional but preferred.
- Davidsons quantity CSV cannot be parsed by itself because it lacks full product data.
- When quantity CSV is provided, join inventory `Item #` to quantity `Item_Number`.
- Use `Item #` as source SKU.
- Use UPC-based canonical SKU when `UPC Code` is present.
- Use source-prefixed fallback SKU when UPC is missing.
- Use `Dealer Price` as unit cost.
- Treat `MSP` as MAP when numeric and greater than zero.
- Preserve `Sale Price` and `Sale Ends`, but source sale pricing remains ignored unless a later pricing feature enables it.
- Quantity tokens such as `A*`, `99+`, and `Call` should not be treated as ordinary exact numbers.
- Allocated/unknown availability should be preserved but not exportable by default.
- Current samples do not include explicit image fields.
- Davidsons media can be enriched best-effort from item-number-based Cloudinary URLs when the source item number is safe to use in a URL.
- Davidsons image URL construction should remain deterministic and offline by default; do not scrape GalleryofGuns product pages during normal conversion.
