from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from inventory_feed_tool.app_state import DesktopAppState, placeholder_conversion_message


class DesktopAppStateTests(unittest.TestCase):
    def test_requires_at_least_one_source_file(self) -> None:
        state = DesktopAppState(output_file=Path("godaddy.csv"))

        self.assertFalse(state.can_convert())
        self.assertIn("Select at least one distributor feed.", state.validation_messages())

    def test_requires_output_file(self) -> None:
        state = DesktopAppState(davidsons_file=Path(__file__))

        self.assertFalse(state.can_convert())
        self.assertIn("Choose an output CSV file.", state.validation_messages())

    def test_requires_csv_output_extension(self) -> None:
        state = DesktopAppState(
            lipseys_file=Path(__file__),
            output_file=Path("godaddy.txt"),
        )

        self.assertFalse(state.can_convert())
        self.assertIn("Output file should use the .csv extension.", state.validation_messages())

    def test_allows_existing_source_and_csv_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "lipseys.csv"
            source.write_text("ITEMNO,UPC\n", encoding="utf-8")
            output = Path(temp_dir) / "godaddy.csv"

            state = DesktopAppState(lipseys_file=source, output_file=output)

            self.assertTrue(state.can_convert())

    def test_placeholder_conversion_message_names_selected_source_count(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "davidsons.csv"
            source.write_text("Item #,UPC Code\n", encoding="utf-8")
            state = DesktopAppState(
                davidsons_file=source,
                output_file=Path(temp_dir) / "godaddy.csv",
            )

            message = placeholder_conversion_message(state)

        self.assertIn("Ready to convert 1 source", message)
        self.assertIn("ETL engine feature", message)


if __name__ == "__main__":
    unittest.main()
