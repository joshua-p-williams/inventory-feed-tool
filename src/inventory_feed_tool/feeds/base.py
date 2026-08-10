from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from inventory_feed_tool.models import SourceOffer
from inventory_feed_tool.parsing import clean_optional_text
from inventory_feed_tool.validation import ValidationMessage


@dataclass(frozen=True)
class FeedParseResult:
    distributor: str
    source_files: tuple[str, ...]
    offers: tuple[SourceOffer, ...]
    messages: tuple[ValidationMessage, ...] = ()
    rows_seen: int = 0
    rows_skipped: int = 0


def read_csv_rows(path: Path) -> tuple[list[dict[str, str]], tuple[str, ...]]:
    with path.open(newline="", encoding="utf-8-sig") as feed_file:
        reader = csv.DictReader(feed_file)
        fieldnames = tuple(reader.fieldnames or ())
        return list(reader), fieldnames


def missing_columns(fieldnames: Iterable[str], required_columns: Iterable[str]) -> tuple[str, ...]:
    available = set(fieldnames)
    return tuple(column for column in required_columns if column not in available)


def row_text(row: dict[str, str], column: str) -> str | None:
    return clean_optional_text(row.get(column))


def first_text(row: dict[str, str], *columns: str) -> str | None:
    for column in columns:
        value = row_text(row, column)
        if value is not None:
            return value
    return None


def source_attributes(row: dict[str, str], mapped_columns: set[str]) -> dict[str, str]:
    attributes: dict[str, str] = {}
    for key, value in row.items():
        if key in mapped_columns:
            continue
        text = clean_optional_text(value)
        if text is not None:
            attributes[key] = text
    return attributes


def row_message(
    severity: str,
    code: str,
    message: str,
    *,
    row_number: int | None = None,
    field: str | None = None,
) -> ValidationMessage:
    suffix = f" Row {row_number}." if row_number is not None else ""
    full_message = f"{message}{suffix}"
    if severity == "error":
        return ValidationMessage.error(code, full_message, field)
    if severity == "warning":
        return ValidationMessage.warning(code, full_message, field)
    return ValidationMessage.info(code, full_message, field)


def basic_description(*parts: str | None, attributes: dict[str, str] | None = None) -> str:
    description_parts = [part for part in parts if part]
    if attributes:
        for key, value in attributes.items():
            if value:
                description_parts.append(f"{key}: {value}")
    return "\n".join(description_parts)

