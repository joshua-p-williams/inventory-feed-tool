# Research

## Prior Feature Decisions

From `0003-canonical-inventory-model`:

- Feed adapters should produce `SourceOffer` objects.
- Source offers preserve source-specific metadata and warnings.
- Pricing behavior comes from `RunConfiguration.pricing`, not distributor-specific hardcoding.
- UPC-based canonical SKUs are the default when UPC is present.
- Source-prefixed fallback SKUs are used when UPC is missing.
- Extra source fields may be preserved in `attributes`.
- Allocated/unknown inventory is preserved but not exportable by default.
- `99+` means an approximate lower-bound quantity of `99`; other `X+` values use `X`.
- FFL/SOT/NFA flags are represented as compliance flags and later exported as description notes.
- Dropshipping is out of scope for the MVP, but dropship fields should be preserved as metadata.

From `0004-local-project-storage`:

- Raw distributor feed files should not be stored in SQLite.
- Source offer snapshots can be stored later as compact metadata.
- Storage is not required for parsing, but parsed offers should contain enough traceability for storage.

## Local Sample Files

Repo-safe reference summaries:

- [Lipseys reference](../../references/lipseys.md)
- [Davidsons reference](../../references/davidsons.md)
- [Local sample feed shapes](../../references/sample-feed-shapes.md)

Sample files reviewed from the parent project folder:

- `../lipseys/in-stock-catalog.csv`
- `../lipseys/default-catalog.csv`
- `../lipseys/accessories-catalog.csv`
- `../davidsons/davidsons_inventory.csv`
- `../davidsons/davidsons_quantity.csv`

These samples should not be copied into the repository unless sanitized and approved.

## Lipseys Sample Shape

The Lipseys catalog files share a 78-column shape. The `in-stock-catalog.csv` sample has 10,356 rows.

Important columns:

- Identity: `ITEMNO`, `UPC`, `MANUFACTURERMODELNO`
- Names/details: `DESCRIPTION1`, `DESCRIPTION2`, `MODEL`, `MANUFACTURER`, `TYPE`, `ITEMTYPE`, `ITEMGROUP`, `FAMILY`
- Attributes: `CALIBERGAUGE`, `ACTION`, `BARRELLENGTH`, `CAPACITY`, `FINISH`, `OVERALLLENGTH`, `SIGHTS`, `STOCKFRAMEGRIPS`, `MAGAZINE`, `CHAMBER`, `RATEOFTWIST`, `FRAME`, `GRIPTYPE`
- Pricing: `PRICE`, `CURRENTPRICE`, `MSRP`, `RETAILMAP`
- Availability: `QUANTITY`, `ALLOCATED`, `CANDROPSHIP`, `ONSALE`, `SPECIAL`
- Shipping/dimensions: `SHIPPINGWEIGHT`, `ITEMLENGTH`, `ITEMWIDTH`, `ITEMHEIGHT`, `PACKAGELENGTH`, `PACKAGEWIDTH`, `PACKAGEHEIGHT`
- Media: `IMAGENAME`
- Compliance: `FFLREQUIRED`, `SOTREQUIRED`

Observed sample data:

- Missing UPC rows: 0
- Missing current price rows: 0
- Rows with MAP greater than zero: 4,772
- Rows where MAP is higher than cost plus 25 percent: 1,908
- Item types in `in-stock-catalog.csv`: Firearm, Accessory, Optic, Ammo

## Lipseys Public Research

Repo-safe reference summary:

- [Lipseys distributor feed reference](../../references/lipseys.md)

Parent-folder downloaded references, not committed to this repository:

- `../references/lipseys/README.md`
- `../references/lipseys/faq.html`
- `../references/lipseys/api-docs.html`
- `../references/lipseys/api-docs-index-BUFpfLqQ.js`
- `../references/lipseys/catalog.html`
- `../references/lipseys/itemdetail-HNH001.html`

Relevant findings:

- `ALLOCATED` means high-demand/short-supply and not guaranteed to be available.
- Adding an item to a cart does not reserve inventory.
- Public site research found image host constants:
  - base: `https://www.lipseyscloud.com/images/`
  - common suffix: `?height=320&width=480&scale=canvas`
  - missing image fallback: `https://www.lipseyscloud.com/images/li-missing-image.png`
- Sample image names were verified as public image URLs.
- Authenticated feed/API endpoints exist, but authenticated retrieval is out of scope.

Lipseys image URL construction:

```text
https://www.lipseyscloud.com/images/{IMAGENAME}?height=320&width=480&scale=canvas
```

If `IMAGENAME` is blank or a missing-image placeholder, leave the image URL blank and attach a warning.

## Davidsons Sample Shape

Davidsons has a catalog/inventory file and a separate warehouse quantity file.

`davidsons_inventory.csv`:

- 10,571 rows
- 21 columns

Important columns:

- Identity: `Item #`, `UPC Code`
- Names/details: `Item Description`, `Manufacturer`, `Gun Type`, `Model Series`
- Attributes: `Caliber`, `Action`, `Capacity`, `Finish`, `Stock`, `Sights`, `Barrel Length`, `Overall Length`, `Features`
- Pricing: `MSP`, `Retail Price`, `Dealer Price`, `Sale Price`, `Sale Ends`
- Availability: `Quantity`

`davidsons_quantity.csv`:

- 10,941 rows
- 4 columns
- Quantity fields: `Quantity_NC`, `Quantity_AZ`
- Join fields: `Item_Number`, `UPC_Code`

Observed sample data:

- Inventory rows with matching quantity rows by item number: 10,557 of 10,571
- Quantity rows not present in inventory: 384
- Missing UPC rows in inventory: 52
- Missing dealer price rows in inventory: 0
- Quantity tokens include `A*` and `99+`

## Davidsons Public Research

Repo-safe reference summary:

- [Davidsons distributor feed reference](../../references/davidsons.md)

Parent-folder downloaded references, not committed to this repository:

- `../references/davidsons/README.md`
- `../references/davidsons/faq.html`

Relevant findings:

- Inventory downloads are available to logged-in dealers.
- FTP inventory download may be available later.
- Davidsons does not backorder items.
- Cart items are not secured until checkout is completed.
- `A` / allocated means demand exceeds supply and the item is unavailable to order online.
- `Call` means quantity requires account-executive confirmation.
- Current sample feeds do not contain image fields.

## Adapter Implications

- Adapters should parse dealer-downloaded files only.
- Adapters should not filter out unavailable rows; they should preserve availability status and warnings.
- Aggregation/source selection will decide what is exportable later.
- Adapters may skip rows that cannot produce required model fields, such as source SKU, product name, unit cost, or any usable identity.
- Tests should use small sanitized CSV strings rather than real sample files.
