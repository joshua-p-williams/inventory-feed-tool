from __future__ import annotations

import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from inventory_feed_tool.app_state import (
    DesktopAppState,
    format_validation_messages,
    format_workflow_result,
)
from inventory_feed_tool.exporters import ExportedFile, GoDaddyExportResult
from inventory_feed_tool.validation import ValidationMessage
from inventory_feed_tool.workflows import NewImportWorkflowResult


class DesktopAppStateTests(unittest.TestCase):
    def test_requires_at_least_one_primary_source_file(self) -> None:
        state = DesktopAppState(output_dir=Path("exports"))

        self.assertFalse(state.can_convert())
        self.assertIn("Select at least one distributor feed.", state.validation_messages())

    def test_requires_output_folder(self) -> None:
        state = DesktopAppState(lipseys_csv=Path(__file__))

        self.assertFalse(state.can_convert())
        self.assertIn("Choose an output folder.", state.validation_messages())

    def test_rejects_davidsons_quantity_without_inventory(self) -> None:
        state = DesktopAppState(
            davidsons_quantity_csv=Path(__file__),
            output_dir=Path("exports"),
        )

        self.assertFalse(state.can_convert())
        self.assertIn(
            "Davidsons quantity CSV requires a Davidsons inventory CSV.",
            state.validation_messages(),
        )

    def test_rejects_output_folder_when_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "exports.csv"
            output_file.write_text("not a folder", encoding="utf-8")
            state = DesktopAppState(lipseys_csv=Path(__file__), output_dir=output_file)

            messages = state.validation_messages()
            can_convert = state.can_convert()

        self.assertFalse(can_convert)
        self.assertTrue(any("Output folder path is an existing file" in message for message in messages))

    def test_rejects_invalid_markup_percent(self) -> None:
        state = DesktopAppState(
            lipseys_csv=Path(__file__),
            output_dir=Path("exports"),
            markup_percent_text="abc",
        )

        self.assertFalse(state.can_convert())
        self.assertIn("Markup percent must be a number.", state.validation_messages())

    def test_rejects_negative_markup_percent(self) -> None:
        state = DesktopAppState(
            lipseys_csv=Path(__file__),
            output_dir=Path("exports"),
            markup_percent_text="-1",
        )

        self.assertFalse(state.can_convert())
        self.assertIn("Markup percent cannot be negative.", state.validation_messages())

    def test_allows_lipseys_only_with_output_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "lipseys.csv"
            source.write_text("ITEMNO,UPC\n", encoding="utf-8")
            output_dir = Path(temp_dir) / "exports"

            state = DesktopAppState(lipseys_csv=source, output_dir=output_dir)

            self.assertTrue(state.can_convert())

    def test_allows_davidsons_inventory_only_with_output_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "davidsons.csv"
            source.write_text("Item #,UPC Code\n", encoding="utf-8")
            output_dir = Path(temp_dir) / "exports"

            state = DesktopAppState(davidsons_inventory_csv=source, output_dir=output_dir)

            self.assertTrue(state.can_convert())

    def test_allows_davidsons_inventory_with_quantity_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            inventory = Path(temp_dir) / "davidsons.csv"
            quantity = Path(temp_dir) / "davidsons_quantity.csv"
            inventory.write_text("Item #,UPC Code\n", encoding="utf-8")
            quantity.write_text("Item_Number,Quantity_NC,Quantity_AZ\n", encoding="utf-8")
            output_dir = Path(temp_dir) / "exports"

            state = DesktopAppState(
                davidsons_inventory_csv=inventory,
                davidsons_quantity_csv=quantity,
                output_dir=output_dir,
            )

            self.assertTrue(state.can_convert())

    def test_builds_new_import_input(self) -> None:
        state = DesktopAppState(
            lipseys_csv=Path("lipseys.csv"),
            davidsons_inventory_csv=Path("davidsons.csv"),
            davidsons_quantity_csv=Path("quantities.csv"),
            output_dir=Path("exports"),
        )

        new_import_input = state.to_new_import_input()

        self.assertEqual(new_import_input.lipseys_csv, Path("lipseys.csv"))
        self.assertEqual(new_import_input.davidsons_inventory_csv, Path("davidsons.csv"))
        self.assertEqual(new_import_input.davidsons_quantity_csv, Path("quantities.csv"))
        self.assertEqual(new_import_input.output_dir, Path("exports"))

    def test_builds_run_configuration(self) -> None:
        state = DesktopAppState(
            lipseys_csv=Path(__file__),
            output_dir=Path("exports"),
            markup_percent_text="18.5",
            include_image_urls=False,
        )

        configuration = state.to_run_configuration()

        self.assertEqual(configuration.pricing.markup_percent, Decimal("18.5"))
        self.assertFalse(configuration.images.include_image_urls)

    def test_run_configuration_raises_when_state_invalid(self) -> None:
        state = DesktopAppState(
            lipseys_csv=Path(__file__),
            output_dir=Path("exports"),
            markup_percent_text="abc",
        )

        with self.assertRaises(ValueError):
            state.to_run_configuration()

    def test_validation_message_formatting(self) -> None:
        formatted = format_validation_messages(["Choose an output folder.", "Markup percent must be a number."])

        self.assertIn("Validation failed.", formatted)
        self.assertIn("- Choose an output folder.", formatted)
        self.assertIn("- Markup percent must be a number.", formatted)

    def test_workflow_result_formatter_includes_output_files_on_partial_success(self) -> None:
        result = NewImportWorkflowResult(
            export_result=GoDaddyExportResult(
                files=(ExportedFile(path=Path("exports/godaddy-import-001.csv"), row_count=1),),
                products_seen=2,
                products_exported=1,
                products_skipped=0,
            ),
            messages=(
                ValidationMessage.error(
                    "lipseys_missing_unit_cost",
                    "Missing unit cost. Row 2.",
                    "unit_cost",
                ),
            ),
            source_rows_seen=2,
            source_rows_skipped=1,
            source_offers_parsed=1,
            product_groups=1,
            products_exported=1,
        )

        formatted = format_workflow_result(result, log_path=Path("exports/conversion-log-20260810-143012.txt"))

        self.assertIn("Completed with errors.", formatted)
        self.assertIn("Products exported: 1", formatted)
        self.assertIn("exports/godaddy-import-001.csv", formatted)
        self.assertIn("exports/conversion-log-20260810-143012.txt", formatted)
        self.assertIn("ERROR lipseys_missing_unit_cost (unit_cost): 1", formatted)
        self.assertNotIn("Missing unit cost. Row 2.", formatted)

    def test_workflow_result_formatter_includes_validation_errors(self) -> None:
        result = NewImportWorkflowResult(
            messages=(ValidationMessage.error("new_import_missing_source", "Select at least one source feed."),),
        )

        formatted = format_workflow_result(result)

        self.assertIn("Validation failed.", formatted)
        self.assertIn("ERROR new_import_missing_source: 1", formatted)
        self.assertNotIn("Select at least one source feed.", formatted)


if __name__ == "__main__":
    unittest.main()
