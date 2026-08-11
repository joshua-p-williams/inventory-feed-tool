from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from inventory_feed_tool.aggregation import (
    AggregationResult,
    SourceSelectionOverride,
    aggregate_source_offers,
)
from inventory_feed_tool.exporters.godaddy import GoDaddyExportResult, export_godaddy_csv
from inventory_feed_tool.feeds import FeedParseResult, parse_davidsons_inventory_csv, parse_lipseys_csv
from inventory_feed_tool.models import ExportMode, RunConfiguration, SourceOffer
from inventory_feed_tool.validation import MessageSeverity, ValidationMessage


@dataclass(frozen=True)
class NewImportInput:
    lipseys_csv: Path | None = None
    davidsons_inventory_csv: Path | None = None
    davidsons_quantity_csv: Path | None = None
    output_dir: Path | None = None


@dataclass(frozen=True)
class NewImportWorkflowResult:
    feed_results: tuple[FeedParseResult, ...] = ()
    aggregation_result: AggregationResult | None = None
    export_result: GoDaddyExportResult | None = None
    messages: tuple[ValidationMessage, ...] = ()
    source_rows_seen: int = 0
    source_rows_skipped: int = 0
    source_offers_parsed: int = 0
    product_groups: int = 0
    product_groups_dropped: int = 0
    products_exported: int = 0
    products_skipped: int = 0

    @property
    def has_errors(self) -> bool:
        return any(message.severity == MessageSeverity.ERROR for message in self.messages)


def run_new_import_workflow(
    inputs: NewImportInput,
    configuration: RunConfiguration | None = None,
    *,
    overrides: Iterable[SourceSelectionOverride] = (),
    filename_prefix: str = "godaddy-import",
) -> NewImportWorkflowResult:
    configuration = configuration or RunConfiguration()
    preflight_messages = _preflight_messages(inputs, configuration)
    if _has_errors(preflight_messages):
        return NewImportWorkflowResult(messages=preflight_messages)

    feed_results = _parse_feeds(inputs, configuration)
    offers = _source_offers(feed_results)
    aggregation_result = aggregate_source_offers(offers, configuration, overrides)
    if inputs.output_dir is None:
        raise RuntimeError("output_dir is required after preflight validation")

    export_result = export_godaddy_csv(
        aggregation_result.products,
        inputs.output_dir,
        configuration,
        filename_prefix=filename_prefix,
    )
    messages = (
        *preflight_messages,
        *tuple(message for result in feed_results for message in result.messages),
        *aggregation_result.messages,
        *export_result.messages,
    )

    return NewImportWorkflowResult(
        feed_results=feed_results,
        aggregation_result=aggregation_result,
        export_result=export_result,
        messages=messages,
        source_rows_seen=sum(result.rows_seen for result in feed_results),
        source_rows_skipped=sum(result.rows_skipped for result in feed_results),
        source_offers_parsed=len(offers),
        product_groups=aggregation_result.product_group_count,
        product_groups_dropped=aggregation_result.product_groups_dropped,
        products_exported=export_result.products_exported,
        products_skipped=export_result.products_skipped,
    )


def _preflight_messages(
    inputs: NewImportInput,
    configuration: RunConfiguration,
) -> tuple[ValidationMessage, ...]:
    messages: list[ValidationMessage] = []
    primary_sources = (inputs.lipseys_csv, inputs.davidsons_inventory_csv)

    if all(path is None for path in primary_sources):
        messages.append(
            ValidationMessage.error(
                "new_import_missing_source",
                "Select at least one source feed.",
                "source",
            )
        )

    if inputs.davidsons_quantity_csv is not None and inputs.davidsons_inventory_csv is None:
        messages.append(
            ValidationMessage.error(
                "new_import_davidsons_quantity_without_inventory",
                "Davidsons quantity CSV requires a Davidsons inventory CSV.",
                "davidsons_quantity_csv",
            )
        )

    if inputs.output_dir is None:
        messages.append(
            ValidationMessage.error(
                "new_import_missing_output_dir",
                "Choose an output folder for generated CSV files.",
                "output_dir",
            )
        )
    elif inputs.output_dir.exists() and not inputs.output_dir.is_dir():
        messages.append(
            ValidationMessage.error(
                "new_import_output_dir_is_file",
                f"Output folder path is an existing file: {inputs.output_dir}",
                "output_dir",
            )
        )

    for field, path in (
        ("lipseys_csv", inputs.lipseys_csv),
        ("davidsons_inventory_csv", inputs.davidsons_inventory_csv),
        ("davidsons_quantity_csv", inputs.davidsons_quantity_csv),
    ):
        if path is not None and not path.is_file():
            messages.append(
                ValidationMessage.error(
                    "new_import_source_file_not_found",
                    f"Source file does not exist or is not a file: {path}",
                    field,
                )
            )

    if configuration.export_mode == ExportMode.UPDATE:
        messages.append(
            ValidationMessage.error(
                "new_import_update_mode_not_supported",
                "New-import workflow does not support update mode yet.",
                "export_mode",
            )
        )

    return tuple(messages)


def _parse_feeds(
    inputs: NewImportInput,
    configuration: RunConfiguration,
) -> tuple[FeedParseResult, ...]:
    results: list[FeedParseResult] = []
    if inputs.lipseys_csv is not None:
        results.append(parse_lipseys_csv(inputs.lipseys_csv, configuration))
    if inputs.davidsons_inventory_csv is not None:
        results.append(
            parse_davidsons_inventory_csv(
                inputs.davidsons_inventory_csv,
                configuration,
                quantity_path=inputs.davidsons_quantity_csv,
            )
        )
    return tuple(results)


def _source_offers(feed_results: Iterable[FeedParseResult]) -> tuple[SourceOffer, ...]:
    return tuple(offer for result in feed_results for offer in result.offers)


def _has_errors(messages: Iterable[ValidationMessage]) -> bool:
    return any(message.severity == MessageSeverity.ERROR for message in messages)
