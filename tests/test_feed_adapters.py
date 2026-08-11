from __future__ import annotations

import csv
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from inventory_feed_tool.feeds.davidsons import parse_davidsons_inventory_csv
from inventory_feed_tool.feeds.lipseys import lipseys_image_url, parse_lipseys_csv
from inventory_feed_tool.models import (
    AvailabilityStatus,
    PricingProfile,
    RunConfiguration,
)


class FeedAdapterTests(unittest.TestCase):
    def test_lipseys_parses_valid_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "lipseys.csv"
            self._write_csv(path, LIPSEYS_COLUMNS, [self._lipseys_row()])

            result = parse_lipseys_csv(path, RunConfiguration())

        self.assertEqual(result.rows_seen, 1)
        self.assertEqual(result.rows_skipped, 0)
        self.assertEqual(len(result.offers), 1)
        offer = result.offers[0]
        self.assertEqual(offer.source.distributor, "lipseys")
        self.assertEqual(offer.source.source_sku, "LIP-1")
        self.assertEqual(offer.identity.canonical_sku, "UPC-736676037018")
        self.assertEqual(offer.identity.upc, "736676037018")
        self.assertEqual(offer.pricing.unit_cost, Decimal("400.00"))
        self.assertEqual(offer.pricing.map_price, Decimal("525.00"))
        self.assertEqual(offer.pricing.calculated_price, Decimal("525.00"))
        self.assertEqual(offer.inventory.status, AvailabilityStatus.AVAILABLE)
        self.assertEqual(offer.inventory.quantity, 3)
        self.assertTrue(offer.compliance.ffl_required)
        self.assertFalse(offer.compliance.sot_required)
        self.assertEqual(
            offer.media.image_url,
            "https://www.lipseyscloud.com/images/sample.jpg?height=320&width=480&scale=canvas",
        )
        self.assertEqual(offer.attributes["CANDROPSHIP"], "Y")

    def test_lipseys_missing_upc_uses_source_fallback_and_warns(self) -> None:
        row = self._lipseys_row(UPC="")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "lipseys.csv"
            self._write_csv(path, LIPSEYS_COLUMNS, [row])

            result = parse_lipseys_csv(path, RunConfiguration())

        self.assertEqual(result.offers[0].identity.canonical_sku, "LIP-LIP-1")
        self.assertTrue(any(message.code == "lipseys_missing_upc" for message in result.messages))

    def test_lipseys_invalid_upc_uses_source_fallback_and_warns(self) -> None:
        row = self._lipseys_row(UPC="NOT-A-UPC")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "lipseys.csv"
            self._write_csv(path, LIPSEYS_COLUMNS, [row])

            result = parse_lipseys_csv(path, RunConfiguration())

        self.assertEqual(result.offers[0].identity.canonical_sku, "LIP-LIP-1")
        self.assertTrue(any(message.code == "lipseys_invalid_upc" for message in result.messages))

    def test_lipseys_allocated_row_is_preserved_not_exportable_by_default(self) -> None:
        row = self._lipseys_row(ALLOCATED="Y", QUANTITY="5")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "lipseys.csv"
            self._write_csv(path, LIPSEYS_COLUMNS, [row])

            result = parse_lipseys_csv(path, RunConfiguration())

        availability = result.offers[0].inventory
        self.assertEqual(availability.status, AvailabilityStatus.ALLOCATED)
        self.assertEqual(availability.quantity, 0)
        self.assertFalse(availability.is_exportable_by_default)

    def test_lipseys_image_helper_ignores_missing_placeholder(self) -> None:
        self.assertIsNone(lipseys_image_url(""))
        self.assertIsNone(lipseys_image_url("li-missing-image.png"))

    def test_lipseys_invalid_unit_cost_skips_row(self) -> None:
        row = self._lipseys_row(CURRENTPRICE="", PRICE="")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "lipseys.csv"
            self._write_csv(path, LIPSEYS_COLUMNS, [row])

            result = parse_lipseys_csv(path, RunConfiguration())

        self.assertEqual(result.rows_skipped, 1)
        self.assertEqual(result.offers, ())
        self.assertTrue(any(message.code == "lipseys_missing_unit_cost" for message in result.messages))

    def test_lipseys_invalid_quantity_warns_and_becomes_unknown(self) -> None:
        row = self._lipseys_row(QUANTITY="many")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "lipseys.csv"
            self._write_csv(path, LIPSEYS_COLUMNS, [row])

            result = parse_lipseys_csv(path, RunConfiguration())

        self.assertEqual(result.offers[0].inventory.status, AvailabilityStatus.UNKNOWN)
        self.assertFalse(result.offers[0].inventory.is_exportable_by_default)
        self.assertTrue(any(message.code == "lipseys_invalid_quantity" for message in result.messages))

    def test_lipseys_approximate_quantity_warns(self) -> None:
        row = self._lipseys_row(QUANTITY="99+")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "lipseys.csv"
            self._write_csv(path, LIPSEYS_COLUMNS, [row])

            result = parse_lipseys_csv(path, RunConfiguration())

        self.assertEqual(result.offers[0].inventory.quantity, 99)
        self.assertTrue(any(message.code == "lipseys_approximate_quantity" for message in result.messages))

    def test_lipseys_invalid_optional_number_warns(self) -> None:
        row = self._lipseys_row(MSRP="retailish")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "lipseys.csv"
            self._write_csv(path, LIPSEYS_COLUMNS, [row])

            result = parse_lipseys_csv(path, RunConfiguration())

        self.assertIsNone(result.offers[0].pricing.msrp)
        self.assertTrue(any(message.code == "lipseys_invalid_optional_number" for message in result.messages))

    def test_lipseys_pricing_uses_supplied_configuration(self) -> None:
        row = self._lipseys_row(RETAILMAP="")
        configuration = RunConfiguration(pricing=PricingProfile(markup_percent=Decimal("10")))
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "lipseys.csv"
            self._write_csv(path, LIPSEYS_COLUMNS, [row])

            result = parse_lipseys_csv(path, configuration)

        self.assertEqual(result.offers[0].pricing.calculated_price, Decimal("440.00"))

    def test_davidsons_parses_valid_row_without_quantity_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            inventory_path = Path(temp_dir) / "davidsons_inventory.csv"
            self._write_csv(inventory_path, DAVIDSONS_COLUMNS, [self._davidsons_row(**{"UPC Code": "#736676037018#"})])

            result = parse_davidsons_inventory_csv(inventory_path, RunConfiguration())

        self.assertEqual(result.rows_seen, 1)
        self.assertEqual(result.rows_skipped, 0)
        offer = result.offers[0]
        self.assertEqual(offer.source.distributor, "davidsons")
        self.assertEqual(offer.source.source_sku, "DAV-1")
        self.assertEqual(offer.identity.canonical_sku, "UPC-736676037018")
        self.assertEqual(offer.identity.upc, "736676037018")
        self.assertEqual(offer.pricing.unit_cost, Decimal("400.00"))
        self.assertEqual(offer.pricing.map_price, Decimal("525.00"))
        self.assertEqual(offer.pricing.calculated_price, Decimal("525.00"))
        self.assertEqual(offer.inventory.quantity, 2)
        self.assertEqual(
            offer.media.image_url,
            "https://res.cloudinary.com/davidsons-inc/image/upload/media/catalog/product/d/a/DAV-1.jpg",
        )
        self.assertEqual(offer.media.image_name, "DAV-1.jpg")
        self.assertEqual(offer.media.image_source, "davidsons_cloudinary_item_number")

    def test_davidsons_quantity_file_merges_warehouse_quantities(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            inventory_path = Path(temp_dir) / "davidsons_inventory.csv"
            quantity_path = Path(temp_dir) / "davidsons_quantity.csv"
            self._write_csv(inventory_path, DAVIDSONS_COLUMNS, [self._davidsons_row(Quantity="0")])
            self._write_csv(
                quantity_path,
                DAVIDSONS_QUANTITY_COLUMNS,
                [self._davidsons_quantity_row(Quantity_NC="2", Quantity_AZ="99+")],
            )

            result = parse_davidsons_inventory_csv(
                inventory_path,
                RunConfiguration(),
                quantity_path=quantity_path,
            )

        availability = result.offers[0].inventory
        self.assertEqual(availability.status, AvailabilityStatus.AVAILABLE)
        self.assertEqual(availability.quantity, 101)
        self.assertEqual(availability.raw_quantity, "2/99+")

    def test_davidsons_quantity_file_allocated_when_no_known_quantity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            inventory_path = Path(temp_dir) / "davidsons_inventory.csv"
            quantity_path = Path(temp_dir) / "davidsons_quantity.csv"
            self._write_csv(inventory_path, DAVIDSONS_COLUMNS, [self._davidsons_row(Quantity="0")])
            self._write_csv(
                quantity_path,
                DAVIDSONS_QUANTITY_COLUMNS,
                [self._davidsons_quantity_row(Quantity_NC="A*", Quantity_AZ="0")],
            )

            result = parse_davidsons_inventory_csv(
                inventory_path,
                RunConfiguration(),
                quantity_path=quantity_path,
            )

        self.assertEqual(result.offers[0].inventory.status, AvailabilityStatus.ALLOCATED)
        self.assertFalse(result.offers[0].inventory.is_exportable_by_default)

    def test_davidsons_missing_quantity_match_warns_and_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            inventory_path = Path(temp_dir) / "davidsons_inventory.csv"
            quantity_path = Path(temp_dir) / "davidsons_quantity.csv"
            self._write_csv(inventory_path, DAVIDSONS_COLUMNS, [self._davidsons_row(Quantity="4")])
            self._write_csv(
                quantity_path,
                DAVIDSONS_QUANTITY_COLUMNS,
                [self._davidsons_quantity_row(Item_Number="OTHER")],
            )

            result = parse_davidsons_inventory_csv(
                inventory_path,
                RunConfiguration(),
                quantity_path=quantity_path,
            )

        self.assertEqual(result.offers[0].inventory.quantity, 4)
        self.assertTrue(any(message.code == "davidsons_missing_quantity_match" for message in result.messages))

    def test_davidsons_missing_upc_uses_source_fallback_and_warns(self) -> None:
        row = self._davidsons_row(**{"UPC Code": ""})
        with tempfile.TemporaryDirectory() as temp_dir:
            inventory_path = Path(temp_dir) / "davidsons_inventory.csv"
            self._write_csv(inventory_path, DAVIDSONS_COLUMNS, [row])

            result = parse_davidsons_inventory_csv(inventory_path, RunConfiguration())

        self.assertEqual(result.offers[0].identity.canonical_sku, "DAV-DAV-1")
        self.assertIsNone(result.offers[0].identity.upc)
        self.assertTrue(any(message.code == "davidsons_missing_upc" for message in result.messages))

    def test_davidsons_invalid_upc_uses_source_fallback_and_warns(self) -> None:
        row = self._davidsons_row(**{"UPC Code": "NOT-A-UPC"})
        with tempfile.TemporaryDirectory() as temp_dir:
            inventory_path = Path(temp_dir) / "davidsons_inventory.csv"
            self._write_csv(inventory_path, DAVIDSONS_COLUMNS, [row])

            result = parse_davidsons_inventory_csv(inventory_path, RunConfiguration())

        self.assertEqual(result.offers[0].identity.canonical_sku, "DAV-DAV-1")
        self.assertIsNone(result.offers[0].identity.upc)
        self.assertTrue(any(message.code == "davidsons_invalid_upc" for message in result.messages))

    def test_davidsons_unsafe_image_item_number_leaves_media_blank(self) -> None:
        row = self._davidsons_row(**{"Item #": "BAD/SKU"})
        with tempfile.TemporaryDirectory() as temp_dir:
            inventory_path = Path(temp_dir) / "davidsons_inventory.csv"
            self._write_csv(inventory_path, DAVIDSONS_COLUMNS, [row])

            result = parse_davidsons_inventory_csv(inventory_path, RunConfiguration())

        self.assertIsNone(result.offers[0].media.image_url)
        self.assertIsNone(result.offers[0].media.image_name)
        self.assertIsNone(result.offers[0].media.image_source)

    def test_davidsons_invalid_unit_cost_skips_row(self) -> None:
        row = self._davidsons_row(**{"Dealer Price": ""})
        with tempfile.TemporaryDirectory() as temp_dir:
            inventory_path = Path(temp_dir) / "davidsons_inventory.csv"
            self._write_csv(inventory_path, DAVIDSONS_COLUMNS, [row])

            result = parse_davidsons_inventory_csv(inventory_path, RunConfiguration())

        self.assertEqual(result.rows_skipped, 1)
        self.assertEqual(result.offers, ())
        self.assertTrue(any(message.code == "davidsons_missing_unit_cost" for message in result.messages))

    def test_davidsons_invalid_inventory_quantity_warns_and_becomes_unknown(self) -> None:
        row = self._davidsons_row(Quantity="many")
        with tempfile.TemporaryDirectory() as temp_dir:
            inventory_path = Path(temp_dir) / "davidsons_inventory.csv"
            self._write_csv(inventory_path, DAVIDSONS_COLUMNS, [row])

            result = parse_davidsons_inventory_csv(inventory_path, RunConfiguration())

        self.assertEqual(result.offers[0].inventory.status, AvailabilityStatus.UNKNOWN)
        self.assertFalse(result.offers[0].inventory.is_exportable_by_default)
        self.assertTrue(any(message.code == "davidsons_invalid_quantity" for message in result.messages))

    def test_davidsons_invalid_warehouse_quantity_warns_and_preserves_other_quantity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            inventory_path = Path(temp_dir) / "davidsons_inventory.csv"
            quantity_path = Path(temp_dir) / "davidsons_quantity.csv"
            self._write_csv(inventory_path, DAVIDSONS_COLUMNS, [self._davidsons_row(Quantity="0")])
            self._write_csv(
                quantity_path,
                DAVIDSONS_QUANTITY_COLUMNS,
                [self._davidsons_quantity_row(Quantity_NC="many", Quantity_AZ="2")],
            )

            result = parse_davidsons_inventory_csv(
                inventory_path,
                RunConfiguration(),
                quantity_path=quantity_path,
            )

        self.assertEqual(result.offers[0].inventory.status, AvailabilityStatus.AVAILABLE)
        self.assertEqual(result.offers[0].inventory.quantity, 2)
        self.assertTrue(any(message.code == "davidsons_invalid_quantity" for message in result.messages))

    def test_davidsons_invalid_optional_number_warns(self) -> None:
        row = self._davidsons_row(MSP="mapish")
        with tempfile.TemporaryDirectory() as temp_dir:
            inventory_path = Path(temp_dir) / "davidsons_inventory.csv"
            self._write_csv(inventory_path, DAVIDSONS_COLUMNS, [row])

            result = parse_davidsons_inventory_csv(inventory_path, RunConfiguration())

        self.assertIsNone(result.offers[0].pricing.map_price)
        self.assertTrue(any(message.code == "davidsons_invalid_optional_number" for message in result.messages))

    def test_davidsons_quantity_missing_required_columns_reports_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            inventory_path = Path(temp_dir) / "davidsons_inventory.csv"
            quantity_path = Path(temp_dir) / "davidsons_quantity.csv"
            self._write_csv(inventory_path, DAVIDSONS_COLUMNS, [self._davidsons_row()])
            self._write_csv(quantity_path, ("Item_Number",), [{"Item_Number": "DAV-1"}])

            result = parse_davidsons_inventory_csv(
                inventory_path,
                RunConfiguration(),
                quantity_path=quantity_path,
            )

        self.assertTrue(any(message.code == "davidsons_quantity_missing_columns" for message in result.messages))

    def _write_csv(self, path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

    def _lipseys_row(self, **overrides: str) -> dict[str, str]:
        row = {column: "" for column in LIPSEYS_COLUMNS}
        row.update(
            {
                "ITEMNO": "LIP-1",
                "DESCRIPTION1": "Sample Lipseys Product",
                "DESCRIPTION2": "Compact pistol",
                "UPC": "736676037018",
                "MANUFACTURERMODELNO": "LIP-MODEL",
                "MSRP": "600.00",
                "MODEL": "Lipseys Model",
                "CALIBERGAUGE": "9mm",
                "MANUFACTURER": "Sample Manufacturer",
                "TYPE": "Pistol",
                "ACTION": "Semi-Auto",
                "BARRELLENGTH": "4",
                "CAPACITY": "10",
                "FINISH": "Black",
                "SIGHTS": "Fixed",
                "STOCKFRAMEGRIPS": "Polymer",
                "MAGAZINE": "1",
                "WEIGHT": "2.1",
                "IMAGENAME": "sample.jpg",
                "SHIPPINGWEIGHT": "3.2",
                "QUANTITY": "3",
                "ALLOCATED": "N",
                "CANDROPSHIP": "Y",
                "ONSALE": "N",
                "PRICE": "410.00",
                "CURRENTPRICE": "400.00",
                "RETAILMAP": "525.00",
                "FFLREQUIRED": "Y",
                "SOTREQUIRED": "N",
                "FAMILY": "Sample Family",
                "ITEMGROUP": "Firearm",
                "PACKAGELENGTH": "12",
                "PACKAGEWIDTH": "8",
                "PACKAGEHEIGHT": "3",
            }
        )
        row.update(overrides)
        return row

    def _davidsons_row(self, **overrides: str) -> dict[str, str]:
        row = {column: "" for column in DAVIDSONS_COLUMNS}
        row.update(
            {
                "Item #": "DAV-1",
                "Item Description": "Sample Davidsons Product",
                "MSP": "525.00",
                "Retail Price": "600.00",
                "Dealer Price": "400.00",
                "Sale Price": "390.00",
                "Sale Ends": "2026-12-31",
                "Quantity": "2",
                "UPC Code": "736676037018",
                "Manufacturer": "Sample Manufacturer",
                "Gun Type": "Pistol",
                "Model Series": "Davidsons Model",
                "Caliber": "9mm",
                "Action": "Semi-Auto",
                "Capacity": "10",
                "Finish": "Black",
                "Stock": "Polymer",
                "Sights": "Fixed",
                "Barrel Length": "4",
                "Overall Length": "7",
                "Features": "Sample features",
            }
        )
        row.update(overrides)
        return row

    def _davidsons_quantity_row(self, **overrides: str) -> dict[str, str]:
        row = {
            "Item_Number": "DAV-1",
            "UPC_Code": "736676037018",
            "Quantity_NC": "2",
            "Quantity_AZ": "1",
        }
        row.update(overrides)
        return row


LIPSEYS_COLUMNS = (
    "ITEMNO",
    "DESCRIPTION1",
    "DESCRIPTION2",
    "UPC",
    "MANUFACTURERMODELNO",
    "MSRP",
    "MODEL",
    "CALIBERGAUGE",
    "MANUFACTURER",
    "TYPE",
    "ACTION",
    "BARRELLENGTH",
    "CAPACITY",
    "FINISH",
    "OVERALLLENGTH",
    "SIGHTS",
    "STOCKFRAMEGRIPS",
    "MAGAZINE",
    "WEIGHT",
    "IMAGENAME",
    "SHIPPINGWEIGHT",
    "QUANTITY",
    "ALLOCATED",
    "CANDROPSHIP",
    "ONSALE",
    "PRICE",
    "CURRENTPRICE",
    "RETAILMAP",
    "FFLREQUIRED",
    "SOTREQUIRED",
    "SPECIAL",
    "FAMILY",
    "ITEMGROUP",
    "PACKAGELENGTH",
    "PACKAGEWIDTH",
    "PACKAGEHEIGHT",
    "COUNTRYOFORIGIN",
)

DAVIDSONS_COLUMNS = (
    "Item #",
    "Item Description",
    "MSP",
    "Retail Price",
    "Dealer Price",
    "Sale Price",
    "Sale Ends",
    "Quantity",
    "UPC Code",
    "Manufacturer",
    "Gun Type",
    "Model Series",
    "Caliber",
    "Action",
    "Capacity",
    "Finish",
    "Stock",
    "Sights",
    "Barrel Length",
    "Overall Length",
    "Features",
)

DAVIDSONS_QUANTITY_COLUMNS = (
    "Item_Number",
    "UPC_Code",
    "Quantity_NC",
    "Quantity_AZ",
)


if __name__ == "__main__":
    unittest.main()
