from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from inventory_feed_tool.models import ImagePolicy, PricingProfile, RunConfiguration
from inventory_feed_tool.validation import MessageSeverity, ValidationMessage
from inventory_feed_tool.workflows import NewImportInput, NewImportWorkflowResult


DEFAULT_MARKUP_PERCENT_TEXT = "25"


@dataclass(frozen=True)
class DesktopAppState:
    """UI-independent state collected by the desktop shell."""

    lipseys_csv: Path | None = None
    davidsons_inventory_csv: Path | None = None
    davidsons_quantity_csv: Path | None = None
    output_dir: Path | None = None
    markup_percent_text: str = DEFAULT_MARKUP_PERCENT_TEXT
    include_image_urls: bool = True

    def selected_source_count(self) -> int:
        return sum(
            1
            for source_file in (self.lipseys_csv, self.davidsons_inventory_csv)
            if source_file is not None
        )

    def validation_messages(self) -> list[str]:
        messages: list[str] = []

        if self.selected_source_count() == 0:
            messages.append("Select at least one distributor feed.")

        if self.davidsons_quantity_csv is not None and self.davidsons_inventory_csv is None:
            messages.append("Davidsons quantity CSV requires a Davidsons inventory CSV.")

        for label, source_file in (
            ("Lipseys CSV", self.lipseys_csv),
            ("Davidsons inventory CSV", self.davidsons_inventory_csv),
            ("Davidsons quantity CSV", self.davidsons_quantity_csv),
        ):
            if source_file is not None and not source_file.is_file():
                messages.append(f"{label} does not exist or is not a file: {source_file}")

        if self.output_dir is None:
            messages.append("Choose an output folder.")
        elif self.output_dir.exists() and not self.output_dir.is_dir():
            messages.append(f"Output folder path is an existing file: {self.output_dir}")

        markup_percent = _parse_markup_percent(self.markup_percent_text)
        if markup_percent is None:
            messages.append("Markup percent must be a number.")
        elif markup_percent < 0:
            messages.append("Markup percent cannot be negative.")

        return messages

    def can_convert(self) -> bool:
        return not self.validation_messages()

    def to_new_import_input(self) -> NewImportInput:
        return NewImportInput(
            lipseys_csv=self.lipseys_csv,
            davidsons_inventory_csv=self.davidsons_inventory_csv,
            davidsons_quantity_csv=self.davidsons_quantity_csv,
            output_dir=self.output_dir,
        )

    def to_run_configuration(self) -> RunConfiguration:
        validation_messages = self.validation_messages()
        if validation_messages:
            raise ValueError("; ".join(validation_messages))

        markup_percent = _parse_markup_percent(self.markup_percent_text)
        if markup_percent is None:
            raise ValueError("markup_percent_text was not parsed after validation")

        return RunConfiguration(
            pricing=PricingProfile(markup_percent=markup_percent),
            images=ImagePolicy(include_image_urls=self.include_image_urls),
        )


def format_validation_messages(messages: list[str]) -> str:
    if not messages:
        return ""
    return "Validation failed.\n\nMessages:\n" + "\n".join(f"- {message}" for message in messages)


def format_workflow_result(result: NewImportWorkflowResult) -> str:
    lines = [_result_heading(result), ""]
    lines.extend(
        [
            f"Rows seen: {result.source_rows_seen}",
            f"Rows skipped: {result.source_rows_skipped}",
            f"Offers parsed: {result.source_offers_parsed}",
            f"Product groups: {result.product_groups}",
            f"Product groups dropped: {result.product_groups_dropped}",
            f"Products exported: {result.products_exported}",
            f"Products skipped: {result.products_skipped}",
        ]
    )

    if result.export_result is not None:
        lines.extend(["", "Output files:"])
        if result.export_result.files:
            lines.extend(str(exported_file.path) for exported_file in result.export_result.files)
        else:
            lines.append("No files were written.")

    if result.messages:
        lines.extend(["", "Messages:"])
        lines.extend(_format_message(message) for message in result.messages)

    return "\n".join(lines)


def _result_heading(result: NewImportWorkflowResult) -> str:
    severities = {message.severity for message in result.messages}
    if MessageSeverity.ERROR in severities:
        if result.export_result is None:
            return "Validation failed."
        return "Completed with errors."
    if MessageSeverity.WARNING in severities:
        return "Completed with warnings."
    return "Completed."


def _format_message(message: ValidationMessage) -> str:
    field = f" ({message.field})" if message.field else ""
    return f"{message.severity.value.upper()} {message.code}{field}: {message.message}"


def _parse_markup_percent(value: str) -> Decimal | None:
    try:
        parsed = Decimal(value.strip())
    except (InvalidOperation, ValueError):
        return None

    return parsed if parsed.is_finite() else None
