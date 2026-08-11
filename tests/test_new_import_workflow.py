from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from inventory_feed_tool.models import ExportMode, RunConfiguration
from inventory_feed_tool.workflows import NewImportInput, run_new_import_workflow


class NewImportWorkflowTests(unittest.TestCase):
    def test_lipseys_only_exports_godaddy_csv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            lipseys_path = base / "lipseys.csv"
            output_dir = base / "exports"
            self._write_csv(lipseys_path, LIPSEYS_COLUMNS, [lipseys_row()])

            result = run_new_import_workflow(
                NewImportInput(lipseys_csv=lipseys_path, output_dir=output_dir),
            )

            rows = self._read_csv(result.export_result.files[0].path)

        self.assertFalse(result.has_errors)
        self.assertEqual(result.source_rows_seen, 1)
        self.assertEqual(result.source_rows_skipped, 0)
        self.assertEqual(result.source_offers_parsed, 1)
        self.assertEqual(result.product_groups, 1)
        self.assertEqual(result.product_groups_dropped, 0)
        self.assertEqual(result.products_exported, 1)
        self.assertEqual(rows[0]["SKU"], "UPC-736676037018")
        self.assertEqual(rows[0]["NAME"], "Sample Lipseys Product")

    def test_davidsons_only_exports_godaddy_csv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            inventory_path = base / "davidsons_inventory.csv"
            output_dir = base / "exports"
            self._write_csv(inventory_path, DAVIDSONS_COLUMNS, [davidsons_row()])

            result = run_new_import_workflow(
                NewImportInput(davidsons_inventory_csv=inventory_path, output_dir=output_dir),
            )

        self.assertFalse(result.has_errors)
        self.assertEqual(result.feed_results[0].distributor, "davidsons")
        self.assertEqual(result.source_offers_parsed, 1)
        self.assertEqual(result.products_exported, 1)

    def test_davidsons_quantity_file_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            inventory_path = base / "davidsons_inventory.csv"
            quantity_path = base / "davidsons_quantity.csv"
            output_dir = base / "exports"
            self._write_csv(inventory_path, DAVIDSONS_COLUMNS, [davidsons_row(Quantity="0")])
            self._write_csv(quantity_path, DAVIDSONS_QUANTITY_COLUMNS, [davidsons_quantity_row()])

            result = run_new_import_workflow(
                NewImportInput(
                    davidsons_inventory_csv=inventory_path,
                    davidsons_quantity_csv=quantity_path,
                    output_dir=output_dir,
                ),
            )

            rows = self._read_csv(result.export_result.files[0].path)

        self.assertEqual(rows[0]["ON-HAND QUANTITY"], "3")
        self.assertEqual(result.products_exported, 1)

    def test_combined_sources_aggregate_to_one_exported_product(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            lipseys_path = base / "lipseys.csv"
            inventory_path = base / "davidsons_inventory.csv"
            output_dir = base / "exports"
            self._write_csv(lipseys_path, LIPSEYS_COLUMNS, [lipseys_row()])
            self._write_csv(inventory_path, DAVIDSONS_COLUMNS, [davidsons_row()])

            result = run_new_import_workflow(
                NewImportInput(
                    lipseys_csv=lipseys_path,
                    davidsons_inventory_csv=inventory_path,
                    output_dir=output_dir,
                ),
            )

        self.assertEqual(result.source_rows_seen, 2)
        self.assertEqual(result.source_offers_parsed, 2)
        self.assertEqual(result.product_groups, 1)
        self.assertEqual(result.products_exported, 1)
        self.assertEqual(len(result.feed_results), 2)

    def test_rejects_quantity_file_without_davidsons_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            quantity_path = base / "davidsons_quantity.csv"
            output_dir = base / "exports"
            self._write_csv(quantity_path, DAVIDSONS_QUANTITY_COLUMNS, [davidsons_quantity_row()])

            result = run_new_import_workflow(
                NewImportInput(davidsons_quantity_csv=quantity_path, output_dir=output_dir),
            )

            self.assertFalse(output_dir.exists())

        self.assertTrue(result.has_errors)
        self.assertEqual(result.feed_results, ())
        self.assertIsNone(result.aggregation_result)
        self.assertIsNone(result.export_result)
        self.assertTrue(
            any(message.code == "new_import_davidsons_quantity_without_inventory" for message in result.messages)
        )

    def test_rejects_missing_source_file_before_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            missing_path = base / "missing.csv"
            output_dir = base / "exports"

            result = run_new_import_workflow(
                NewImportInput(lipseys_csv=missing_path, output_dir=output_dir),
            )

        self.assertTrue(result.has_errors)
        self.assertEqual(result.source_rows_seen, 0)
        self.assertTrue(any(message.code == "new_import_source_file_not_found" for message in result.messages))

    def test_rejects_output_dir_when_it_is_an_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            lipseys_path = base / "lipseys.csv"
            output_path = base / "exports.csv"
            self._write_csv(lipseys_path, LIPSEYS_COLUMNS, [lipseys_row()])
            output_path.write_text("not a folder", encoding="utf-8")

            result = run_new_import_workflow(
                NewImportInput(lipseys_csv=lipseys_path, output_dir=output_path),
            )

        self.assertTrue(result.has_errors)
        self.assertTrue(any(message.code == "new_import_output_dir_is_file" for message in result.messages))

    def test_rejects_update_mode_before_exporting(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            lipseys_path = base / "lipseys.csv"
            output_dir = base / "exports"
            self._write_csv(lipseys_path, LIPSEYS_COLUMNS, [lipseys_row()])

            result = run_new_import_workflow(
                NewImportInput(lipseys_csv=lipseys_path, output_dir=output_dir),
                RunConfiguration(export_mode=ExportMode.UPDATE),
            )

            self.assertFalse(output_dir.exists())

        self.assertTrue(result.has_errors)
        self.assertTrue(any(message.code == "new_import_update_mode_not_supported" for message in result.messages))

    def test_preserves_adapter_aggregation_and_exporter_messages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            lipseys_path = base / "lipseys.csv"
            inventory_path = base / "davidsons_inventory.csv"
            output_dir = base / "exports"
            self._write_csv(lipseys_path, LIPSEYS_COLUMNS, [lipseys_row(UPC="", MSRP="retailish")])
            self._write_csv(inventory_path, DAVIDSONS_COLUMNS, [davidsons_row(Quantity="0")])

            result = run_new_import_workflow(
                NewImportInput(
                    lipseys_csv=lipseys_path,
                    davidsons_inventory_csv=inventory_path,
                    output_dir=output_dir,
                ),
            )

        codes = {message.code for message in result.messages}
        self.assertIn("lipseys_missing_upc", codes)
        self.assertIn("lipseys_invalid_optional_number", codes)
        self.assertIn("no_exportable_offer", codes)
        self.assertEqual(result.product_groups, 2)
        self.assertEqual(result.product_groups_dropped, 1)
        self.assertEqual(result.products_exported, 1)

    def test_custom_filename_prefix_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            lipseys_path = base / "lipseys.csv"
            output_dir = base / "exports"
            self._write_csv(lipseys_path, LIPSEYS_COLUMNS, [lipseys_row()])

            result = run_new_import_workflow(
                NewImportInput(lipseys_csv=lipseys_path, output_dir=output_dir),
                filename_prefix="custom-import",
            )

        self.assertEqual(result.export_result.files[0].path.name, "custom-import-001.csv")

    def test_reports_multiple_output_batches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            lipseys_path = base / "lipseys.csv"
            output_dir = base / "exports"
            self._write_csv(
                lipseys_path,
                LIPSEYS_COLUMNS,
                [
                    lipseys_row(ITEMNO=f"LIP-{index}", UPC=f"736676{index:06d}")
                    for index in range(101)
                ],
            )

            result = run_new_import_workflow(
                NewImportInput(lipseys_csv=lipseys_path, output_dir=output_dir),
            )

        self.assertFalse(result.has_errors)
        self.assertEqual(result.products_exported, 101)
        self.assertEqual([file.row_count for file in result.export_result.files], [100, 1])
        self.assertEqual(
            [file.path.name for file in result.export_result.files],
            ["godaddy-import-001.csv", "godaddy-import-002.csv"],
        )

    def _write_csv(self, path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

    def _read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open(newline="", encoding="utf-8") as input_file:
            return list(csv.DictReader(input_file))


def lipseys_row(**overrides: str) -> dict[str, str]:
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


def davidsons_row(**overrides: str) -> dict[str, str]:
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


def davidsons_quantity_row(**overrides: str) -> dict[str, str]:
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
