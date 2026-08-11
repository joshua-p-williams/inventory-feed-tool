from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from inventory_feed_tool.exporters import ExportedFile
from inventory_feed_tool.models import RunConfiguration
from inventory_feed_tool.validation import MessageSeverity, ValidationMessage
from inventory_feed_tool.workflows import NewImportInput, NewImportWorkflowResult


LOG_FILENAME_PREFIX = "conversion-log"
LATEST_LOG_FILENAME = "conversion-log-latest.txt"
DEFAULT_MAX_OUTPUT_FILES = 10


@dataclass(frozen=True)
class MessageSummary:
    severity: MessageSeverity
    code: str
    field: str | None
    count: int


@dataclass(frozen=True)
class WrittenRunLog:
    path: Path
    latest_path: Path | None = None


def summarize_messages(messages: Iterable[ValidationMessage]) -> tuple[MessageSummary, ...]:
    counts = Counter((message.severity, message.code, message.field) for message in messages)
    summaries = (
        MessageSummary(severity=severity, code=code, field=field, count=count)
        for (severity, code, field), count in counts.items()
    )
    return tuple(sorted(summaries, key=_message_summary_sort_key))


def format_compact_run_summary(
    result: NewImportWorkflowResult,
    *,
    log_path: Path | None = None,
    max_output_files: int = DEFAULT_MAX_OUTPUT_FILES,
) -> str:
    if max_output_files < 1:
        raise ValueError("max_output_files must be at least one")

    lines = [_result_heading(result), ""]
    lines.extend(_count_lines(result))

    files = tuple(result.export_result.files if result.export_result is not None else ())
    if result.export_result is not None:
        lines.extend(["", f"Output files: {len(files)}"])
        if files:
            lines.extend(_compact_output_file_lines(files, max_output_files))
        else:
            lines.append("No files were written.")

    if log_path is not None:
        lines.extend(["", "Full log:", str(log_path)])

    message_summaries = summarize_messages(result.messages)
    if message_summaries:
        lines.extend(["", "Message summary:"])
        lines.extend(_format_message_summary(summary) for summary in message_summaries)

    return "\n".join(lines)


def format_full_run_log(
    result: NewImportWorkflowResult,
    *,
    inputs: NewImportInput,
    configuration: RunConfiguration,
) -> str:
    lines = [_result_heading(result), ""]

    lines.extend(
        [
            "Source files:",
            f"Lipseys CSV: {_path_or_not_selected(inputs.lipseys_csv)}",
            f"Davidsons inventory CSV: {_path_or_not_selected(inputs.davidsons_inventory_csv)}",
            f"Davidsons quantity CSV: {_path_or_not_selected(inputs.davidsons_quantity_csv)}",
            f"Output folder: {_path_or_not_selected(inputs.output_dir)}",
            "",
            "Configuration:",
            f"Export mode: {configuration.export_mode.value}",
            f"Markup percent: {configuration.pricing.markup_percent}",
            f"MAP mode: {configuration.pricing.map_mode.value}",
            f"Sale price mode: {configuration.pricing.sale_price_mode.value}",
            f"Rounding mode: {configuration.pricing.rounding_mode.value}",
            f"Include image URLs: {_bool_text(configuration.images.include_image_urls)}",
            f"Missing image behavior: {configuration.images.missing_image_behavior.value}",
            f"Validate image URLs: {_bool_text(configuration.images.validate_image_urls)}",
            f"Include zero quantity: {_bool_text(configuration.availability.include_zero_quantity)}",
            f"Include allocated: {_bool_text(configuration.availability.include_allocated)}",
            f"Include unknown quantity: {_bool_text(configuration.availability.include_unknown_quantity)}",
            f"Allow backorder: {_bool_text(configuration.availability.allow_backorder)}",
            f"Source selection strategy: {configuration.source_selection.strategy.value}",
            f"FFL required behavior: {configuration.compliance.ffl_required_behavior.value}",
            f"SOT required behavior: {configuration.compliance.sot_required_behavior.value}",
            f"NFA item behavior: {configuration.compliance.nfa_item_behavior.value}",
            "",
            "Counts:",
        ]
    )
    lines.extend(_count_lines(result))

    lines.extend(["", "Feed results:"])
    if result.feed_results:
        for feed_result in result.feed_results:
            lines.extend(
                [
                    f"{feed_result.distributor}:",
                    f"  Source files: {', '.join(feed_result.source_files) if feed_result.source_files else '(none)'}",
                    f"  Rows seen: {feed_result.rows_seen}",
                    f"  Rows skipped: {feed_result.rows_skipped}",
                    f"  Offers parsed: {len(feed_result.offers)}",
                    f"  Messages: {len(feed_result.messages)}",
                ]
            )
    else:
        lines.append("No feed results.")

    files = tuple(result.export_result.files if result.export_result is not None else ())
    lines.extend(["", "Output files:"])
    if files:
        for exported_file in files:
            lines.append(f"{exported_file.path} ({exported_file.row_count} rows)")
    else:
        lines.append("No files were written.")

    message_summaries = summarize_messages(result.messages)
    lines.extend(["", "Message summary:"])
    if message_summaries:
        lines.extend(_format_message_summary(summary) for summary in message_summaries)
    else:
        lines.append("No messages.")

    lines.extend(["", "Detailed messages:"])
    if result.messages:
        lines.extend(_format_message(message) for message in result.messages)
    else:
        lines.append("No messages.")

    return "\n".join(lines) + "\n"


def write_run_log(
    output_dir: Path,
    text: str,
    *,
    timestamp: datetime | None = None,
    update_latest: bool = True,
) -> WrittenRunLog:
    timestamp = timestamp or datetime.now()
    output_dir.mkdir(parents=True, exist_ok=True)

    path = _unique_log_path(output_dir, timestamp)
    path.write_text(text, encoding="utf-8")

    latest_path: Path | None = None
    if update_latest:
        latest_path = output_dir / LATEST_LOG_FILENAME
        latest_path.write_text(text, encoding="utf-8")

    return WrittenRunLog(path=path, latest_path=latest_path)


def _count_lines(result: NewImportWorkflowResult) -> list[str]:
    return [
        f"Rows seen: {result.source_rows_seen}",
        f"Rows skipped: {result.source_rows_skipped}",
        f"Offers parsed: {result.source_offers_parsed}",
        f"Product groups: {result.product_groups}",
        f"Product groups dropped: {result.product_groups_dropped}",
        f"Products exported: {result.products_exported}",
        f"Products skipped: {result.products_skipped}",
    ]


def _compact_output_file_lines(files: tuple[ExportedFile, ...], max_output_files: int) -> list[str]:
    paths = [str(exported_file.path) for exported_file in files]
    if len(paths) <= max_output_files:
        return ["Files:", *paths]

    if max_output_files == 1:
        return ["Last file:", paths[-1]]

    first_count = max_output_files - 1
    return [
        "First files:",
        *paths[:first_count],
        "...",
        "Last file:",
        paths[-1],
    ]


def _result_heading(result: NewImportWorkflowResult) -> str:
    severities = {message.severity for message in result.messages}
    if MessageSeverity.ERROR in severities:
        if result.export_result is None:
            return "Validation failed."
        return "Completed with errors."
    if MessageSeverity.WARNING in severities:
        return "Completed with warnings."
    return "Completed."


def _format_message_summary(summary: MessageSummary) -> str:
    field = f" ({summary.field})" if summary.field else ""
    return f"{summary.severity.value.upper()} {summary.code}{field}: {summary.count}"


def _format_message(message: ValidationMessage) -> str:
    field = f" ({message.field})" if message.field else ""
    return f"{message.severity.value.upper()} {message.code}{field}: {message.message}"


def _message_summary_sort_key(summary: MessageSummary) -> tuple[int, int, str, str]:
    return (
        _severity_sort_rank(summary.severity),
        -summary.count,
        summary.code,
        summary.field or "",
    )


def _severity_sort_rank(severity: MessageSeverity) -> int:
    return {
        MessageSeverity.ERROR: 0,
        MessageSeverity.WARNING: 1,
        MessageSeverity.INFO: 2,
    }[severity]


def _unique_log_path(output_dir: Path, timestamp: datetime) -> Path:
    timestamp_text = timestamp.strftime("%Y%m%d-%H%M%S")
    base_path = output_dir / f"{LOG_FILENAME_PREFIX}-{timestamp_text}.txt"
    if not base_path.exists():
        return base_path

    suffix = 2
    while True:
        candidate = output_dir / f"{LOG_FILENAME_PREFIX}-{timestamp_text}-{suffix}.txt"
        if not candidate.exists():
            return candidate
        suffix += 1


def _path_or_not_selected(path: Path | None) -> str:
    return str(path) if path is not None else "(not selected)"


def _bool_text(value: bool) -> str:
    return "yes" if value else "no"
