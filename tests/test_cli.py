from __future__ import annotations

import contextlib
import csv
import io
import tempfile
import unittest
from pathlib import Path

from inventory_feed_tool.cli import main


class CliTests(unittest.TestCase):
    def test_main_prints_ready_message(self) -> None:
        exit_code, output = self._run_cli([])

        self.assertEqual(exit_code, 0)
        self.assertIn("Inventory Feed Tool is ready.", output)

    def test_gui_entry_point_imports_without_starting_tkinter(self) -> None:
        import inventory_feed_tool.gui_app

        self.assertTrue(callable(inventory_feed_tool.gui_app.main))

    def test_new_import_reports_summary_and_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            lipseys_path = base / "lipseys.csv"
            output_dir = base / "exports"
            self._write_csv(lipseys_path, LIPSEYS_COLUMNS, [lipseys_row()])

            exit_code, output = self._run_cli(
                [
                    "new-import",
                    "--lipseys-csv",
                    str(lipseys_path),
                    "--output-dir",
                    str(output_dir),
                ]
            )
            log_files = sorted(path.name for path in output_dir.glob("conversion-log-*.txt"))

        self.assertEqual(exit_code, 0)
        self.assertIn("Completed.", output)
        self.assertIn("Rows seen: 1", output)
        self.assertIn("Offers parsed: 1", output)
        self.assertIn("Products exported: 1", output)
        self.assertIn("Output files: 1", output)
        self.assertIn("godaddy-import-001.csv", output)
        self.assertIn("Full log:", output)
        self.assertTrue(any(name.startswith("conversion-log-") for name in log_files))
        self.assertIn("conversion-log-latest.txt", log_files)

    def test_new_import_reports_files_even_when_row_errors_make_exit_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            lipseys_path = base / "lipseys.csv"
            output_dir = base / "exports"
            self._write_csv(
                lipseys_path,
                LIPSEYS_COLUMNS,
                [lipseys_row(), lipseys_row(ITEMNO="BAD-ROW", UPC="736676999999", CURRENTPRICE="", PRICE="")],
            )

            exit_code, output = self._run_cli(
                [
                    "new-import",
                    "--lipseys-csv",
                    str(lipseys_path),
                    "--output-dir",
                    str(output_dir),
                ]
            )
            log_files = sorted(output_dir.glob("conversion-log-*.txt"))
            timestamped_log = next(path for path in log_files if path.name != "conversion-log-latest.txt")
            log_text = timestamped_log.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 1)
        self.assertIn("Completed with errors.", output)
        self.assertIn("Rows seen: 2", output)
        self.assertIn("Products exported: 1", output)
        self.assertIn("Output files: 1", output)
        self.assertIn("ERROR lipseys_missing_unit_cost (CURRENTPRICE): 1", output)
        self.assertIn("Full log:", output)
        self.assertIn(
            "ERROR lipseys_missing_unit_cost (CURRENTPRICE): "
            "Lipseys row is missing valid CURRENTPRICE or PRICE. Row 3.",
            log_text,
        )

    def test_new_import_validation_failure_returns_nonzero_without_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "exports"

            exit_code, output = self._run_cli(["new-import", "--output-dir", str(output_dir)])

        self.assertEqual(exit_code, 1)
        self.assertIn("Validation failed.", output)
        self.assertIn("ERROR new_import_missing_source (source): 1", output)
        self.assertNotIn("Parsed", output)
        self.assertNotIn("Wrote", output)
        self.assertNotIn("Full log:", output)

    def _run_cli(self, argv: list[str]) -> tuple[int, str]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(argv)
        return exit_code, output.getvalue()

    def _write_csv(self, path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)


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


if __name__ == "__main__":
    unittest.main()
