from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from inventory_feed_tool.exporters import ExportedFile, GoDaddyExportResult
from inventory_feed_tool.feeds import FeedParseResult
from inventory_feed_tool.models import ImagePolicy, PricingProfile, RunConfiguration
from inventory_feed_tool.run_summary import (
    LATEST_LOG_FILENAME,
    format_compact_run_summary,
    format_full_run_log,
    summarize_messages,
    write_run_log,
)
from inventory_feed_tool.validation import MessageSeverity, ValidationMessage
from inventory_feed_tool.workflows import NewImportInput, NewImportWorkflowResult


class RunSummaryTests(unittest.TestCase):
    def test_summarize_messages_groups_and_sorts_by_severity_count_and_code(self) -> None:
        summaries = summarize_messages(
            [
                ValidationMessage.warning("source_warning", "Warning one.", "UPC"),
                ValidationMessage.error("row_error", "Error one.", "PRICE"),
                ValidationMessage.warning("source_warning", "Warning two.", "UPC"),
                ValidationMessage.info("row_info", "Info one.", None),
                ValidationMessage.warning("other_warning", "Warning three.", "SKU"),
            ]
        )

        self.assertEqual(
            [(summary.severity, summary.code, summary.field, summary.count) for summary in summaries],
            [
                (MessageSeverity.ERROR, "row_error", "PRICE", 1),
                (MessageSeverity.WARNING, "source_warning", "UPC", 2),
                (MessageSeverity.WARNING, "other_warning", "SKU", 1),
                (MessageSeverity.INFO, "row_info", None, 1),
            ],
        )

    def test_compact_summary_limits_output_files_and_includes_log_path(self) -> None:
        result = NewImportWorkflowResult(
            export_result=GoDaddyExportResult(
                files=tuple(
                    ExportedFile(path=Path(f"exports/godaddy-import-{index:03}.csv"), row_count=100)
                    for index in range(1, 6)
                ),
                products_exported=500,
            ),
            messages=(
                ValidationMessage.warning("source_warning", "Detailed warning. Row 12.", "UPC"),
                ValidationMessage.warning("source_warning", "Detailed warning. Row 13.", "UPC"),
            ),
            source_rows_seen=500,
            source_offers_parsed=500,
            product_groups=500,
            products_exported=500,
        )

        formatted = format_compact_run_summary(
            result,
            log_path=Path("exports/conversion-log-20260810-143012.txt"),
            max_output_files=3,
        )

        self.assertIn("Completed with warnings.", formatted)
        self.assertIn("Output files: 5", formatted)
        self.assertIn("First files:", formatted)
        self.assertIn("exports/godaddy-import-001.csv", formatted)
        self.assertIn("exports/godaddy-import-002.csv", formatted)
        self.assertNotIn("exports/godaddy-import-003.csv", formatted)
        self.assertIn("Last file:", formatted)
        self.assertIn("exports/godaddy-import-005.csv", formatted)
        self.assertIn("Full log:", formatted)
        self.assertIn("exports/conversion-log-20260810-143012.txt", formatted)
        self.assertIn("WARNING source_warning (UPC): 2", formatted)
        self.assertNotIn("Detailed warning. Row 12.", formatted)

    def test_full_log_includes_inputs_configuration_outputs_and_detailed_messages(self) -> None:
        inputs = NewImportInput(
            lipseys_csv=Path("sources/lipseys.csv"),
            output_dir=Path("exports"),
        )
        configuration = RunConfiguration(
            pricing=PricingProfile(markup_percent=Decimal("18.5")),
            images=ImagePolicy(include_image_urls=False),
        )
        result = NewImportWorkflowResult(
            feed_results=(
                FeedParseResult(
                    distributor="lipseys",
                    source_files=("sources/lipseys.csv",),
                    offers=(),
                    messages=(ValidationMessage.warning("source_warning", "Feed warning.", "UPC"),),
                    rows_seen=2,
                    rows_skipped=1,
                ),
            ),
            export_result=GoDaddyExportResult(
                files=(ExportedFile(path=Path("exports/godaddy-import-001.csv"), row_count=1),),
                products_exported=1,
            ),
            messages=(ValidationMessage.warning("source_warning", "Feed warning. Row 2.", "UPC"),),
            source_rows_seen=2,
            source_rows_skipped=1,
            source_offers_parsed=1,
            product_groups=1,
            products_exported=1,
        )

        formatted = format_full_run_log(result, inputs=inputs, configuration=configuration)

        self.assertIn("Source files:", formatted)
        self.assertIn("Lipseys CSV: sources/lipseys.csv", formatted)
        self.assertIn("Configuration:", formatted)
        self.assertIn("Markup percent: 18.5", formatted)
        self.assertIn("Include image URLs: no", formatted)
        self.assertIn("Feed results:", formatted)
        self.assertIn("lipseys:", formatted)
        self.assertIn("exports/godaddy-import-001.csv (1 rows)", formatted)
        self.assertIn("WARNING source_warning (UPC): 1", formatted)
        self.assertIn("WARNING source_warning (UPC): Feed warning. Row 2.", formatted)

    def test_write_run_log_creates_timestamped_and_latest_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            timestamp = datetime(2026, 8, 10, 14, 30, 12)

            first = write_run_log(output_dir, "first log", timestamp=timestamp)
            second = write_run_log(output_dir, "second log", timestamp=timestamp)

            self.assertEqual(first.path.name, "conversion-log-20260810-143012.txt")
            self.assertEqual(second.path.name, "conversion-log-20260810-143012-2.txt")
            self.assertEqual(first.path.read_text(encoding="utf-8"), "first log")
            self.assertEqual(second.path.read_text(encoding="utf-8"), "second log")
            self.assertEqual(first.latest_path, output_dir / LATEST_LOG_FILENAME)
            self.assertEqual((output_dir / LATEST_LOG_FILENAME).read_text(encoding="utf-8"), "second log")


if __name__ == "__main__":
    unittest.main()
