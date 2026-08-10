# Local Sample Feed Shapes

Reviewed: 2026-08-08 and 2026-08-09

This document summarizes structural findings from local sample files without committing raw distributor inventory data.

Sample files reviewed outside the repository:

- `../godaddy_product_import_template.csv`
- `../lipseys/in-stock-catalog.csv`
- `../lipseys/default-catalog.csv`
- `../lipseys/accessories-catalog.csv`
- `../davidsons/davidsons_inventory.csv`
- `../davidsons/davidsons_quantity.csv`

Raw sample files should not be copied into the repository unless sanitized and approved.

## GoDaddy Template

Observed column count: 37

Columns:

```text
SKU,EAN,UPC,GTIN,ISBN,TYPE,NAME,PRODUCT ID,VARIANT GROUP ID,SHORTCODE,MANUFACTURER,MODEL NUMBER,MSRP,BRAND,STATUS,PRICE,SALE PRICE,UNIT COST,ALLOW CUSTOM PRICE,ON-HAND QUANTITY,TRACK INVENTORY,ALLOW BACKORDER,DESCRIPTION,DISABLE SHIPPING,FREE SHIPPING,FIXED SHIPPING FEE,WEIGHT,LENGTH,WIDTH,HEIGHT,IMAGE URL,OPTION 1 NAME,OPTION 1 VALUE,OPTION 2 NAME,OPTION 2 VALUE,OPTION 3 NAME,OPTION 3 VALUE
```

## Lipseys Samples

Observed files:

- `default-catalog.csv`: 19,012 rows, 78 columns
- `accessories-catalog.csv`: 5,406 rows, 78 columns
- `in-stock-catalog.csv`: 10,356 rows, 78 columns

Observed item type counts in `in-stock-catalog.csv`:

- Firearm: 6,696
- Accessory: 3,008
- Optic: 591
- Ammo: 61

Observed data quality:

- Missing UPC rows: 0
- Missing current price rows: 0
- Rows with MAP greater than zero: 4,772
- Rows where MAP is higher than cost plus 25 percent: 1,908

## Davidsons Samples

Observed files:

- `davidsons_inventory.csv`: 10,571 rows, 21 columns
- `davidsons_quantity.csv`: 10,941 rows, 4 columns

Observed data quality:

- Inventory rows with matching quantity rows by item number: 10,557 of 10,571
- Quantity rows not present in inventory: 384
- Missing UPC rows in inventory: 52
- Missing dealer price rows in inventory: 0
- Inventory `Quantity` tokens include `A*` and `99+`
- Quantity detail `Quantity_NC` and `Quantity_AZ` tokens include `A*` and `99+`

## Cross-Distributor Overlap

Earlier local analysis found 4,172 overlapping UPCs between Lipseys in-stock rows and Davidsons inventory rows.

Implication: aggregation must group by stable product identity, preferably UPC, while preserving distributor-specific source offers.

