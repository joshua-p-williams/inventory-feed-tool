from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable, Protocol

from inventory_feed_tool.models import CanonicalProduct, ExportMode, RunConfiguration, SourceOffer
from inventory_feed_tool.validation import ValidationMessage


GODADDY_COLUMNS = (
    "SKU",
    "EAN",
    "UPC",
    "GTIN",
    "ISBN",
    "TYPE",
    "NAME",
    "PRODUCT ID",
    "VARIANT GROUP ID",
    "SHORTCODE",
    "MANUFACTURER",
    "MODEL NUMBER",
    "MSRP",
    "BRAND",
    "STATUS",
    "PRICE",
    "SALE PRICE",
    "UNIT COST",
    "ALLOW CUSTOM PRICE",
    "ON-HAND QUANTITY",
    "TRACK INVENTORY",
    "ALLOW BACKORDER",
    "DESCRIPTION",
    "DISABLE SHIPPING",
    "FREE SHIPPING",
    "FIXED SHIPPING FEE",
    "WEIGHT",
    "LENGTH",
    "WIDTH",
    "HEIGHT",
    "IMAGE URL",
    "OPTION 1 NAME",
    "OPTION 1 VALUE",
    "OPTION 2 NAME",
    "OPTION 2 VALUE",
    "OPTION 3 NAME",
    "OPTION 3 VALUE",
)

DEFAULT_BATCH_SIZE = 100
DEFAULT_FILENAME_PREFIX = "godaddy-import"
SUPPORTED_PRODUCT_TYPES = {"PHYSICAL"}
SUPPORTED_STATUSES = {"ACTIVE", "DRAFT", "ARCHIVED"}


class ProductIdLookup(Protocol):
    def find_product_id(self, product: CanonicalProduct) -> str | None:
        ...


@dataclass(frozen=True)
class ExportedFile:
    path: Path
    row_count: int


@dataclass(frozen=True)
class GoDaddyExportResult:
    files: tuple[ExportedFile, ...]
    messages: tuple[ValidationMessage, ...] = ()
    products_seen: int = 0
    products_exported: int = 0
    products_skipped: int = 0


def export_godaddy_csv(
    products: Iterable[CanonicalProduct],
    output_dir: Path,
    configuration: RunConfiguration | None = None,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    filename_prefix: str = DEFAULT_FILENAME_PREFIX,
    product_id_lookup: ProductIdLookup | None = None,
) -> GoDaddyExportResult:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")

    configuration = configuration or RunConfiguration()
    product_list = tuple(products)

    if configuration.export_mode == ExportMode.UPDATE:
        return GoDaddyExportResult(
            files=(),
            messages=(
                ValidationMessage.error(
                    "godaddy_update_mode_not_supported",
                    "GoDaddy update-mode export is not supported until product ID sync is implemented.",
                    "PRODUCT ID",
                ),
            ),
            products_seen=len(product_list),
            products_exported=0,
            products_skipped=len(product_list),
        )

    rows: list[dict[str, str]] = []
    messages: list[ValidationMessage] = []
    skipped = 0
    for product in product_list:
        row, row_messages = _build_new_import_row(product, configuration)
        messages.extend(row_messages)
        if row is None:
            skipped += 1
            continue
        rows.append(row)

    if not rows:
        return GoDaddyExportResult(
            files=(),
            messages=tuple(messages),
            products_seen=len(product_list),
            products_exported=0,
            products_skipped=skipped,
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    files = tuple(_write_batches(rows, output_dir, batch_size, filename_prefix))
    return GoDaddyExportResult(
        files=files,
        messages=tuple(messages),
        products_seen=len(product_list),
        products_exported=len(rows),
        products_skipped=skipped,
    )


def _build_new_import_row(
    product: CanonicalProduct,
    configuration: RunConfiguration,
) -> tuple[dict[str, str] | None, tuple[ValidationMessage, ...]]:
    offer = product.selected_offer
    if offer is None:
        return None, (
            ValidationMessage.warning(
                "godaddy_missing_selected_offer",
                f"Product {product.identity.canonical_sku} has no selected offer and was skipped.",
                "selected_offer",
            ),
        )

    required_messages = _required_field_messages(product, offer)
    if required_messages:
        return None, required_messages

    row = dict.fromkeys(GODADDY_COLUMNS, "")
    row.update(
        {
            "SKU": _text(product.identity.canonical_sku),
            "EAN": _text(product.identity.ean),
            "UPC": _text(product.identity.upc),
            "GTIN": _text(product.identity.gtin),
            "ISBN": _text(product.identity.isbn),
            "TYPE": _enum_text(product.details.product_type, default="PHYSICAL"),
            "NAME": _text(product.details.name),
            "PRODUCT ID": "",
            "VARIANT GROUP ID": "",
            "SHORTCODE": "",
            "MANUFACTURER": _text(product.identity.manufacturer),
            "MODEL NUMBER": _text(product.identity.model_number),
            "MSRP": _money(offer.pricing.msrp),
            "BRAND": _text(product.identity.brand),
            "STATUS": _enum_text(product.details.status, default="ACTIVE"),
            "PRICE": _money(offer.pricing.calculated_price),
            "SALE PRICE": _money(offer.pricing.sale_price),
            "UNIT COST": _money(offer.pricing.unit_cost),
            "ALLOW CUSTOM PRICE": _bool(False),
            "ON-HAND QUANTITY": _quantity(offer.inventory.quantity),
            "TRACK INVENTORY": _bool(offer.inventory.track_inventory),
            "ALLOW BACKORDER": _bool(offer.inventory.allow_backorder),
            "DESCRIPTION": _description(product, offer, configuration),
            "DISABLE SHIPPING": _bool(offer.shipping.disable_shipping),
            "FREE SHIPPING": _bool(offer.shipping.free_shipping),
            "FIXED SHIPPING FEE": _money(offer.shipping.fixed_shipping_fee),
            "WEIGHT": _decimal(offer.shipping.weight),
            "LENGTH": _decimal(offer.shipping.length),
            "WIDTH": _decimal(offer.shipping.width),
            "HEIGHT": _decimal(offer.shipping.height),
            "IMAGE URL": _text(offer.media.image_url) if configuration.images.include_image_urls else "",
            "OPTION 1 NAME": "",
            "OPTION 1 VALUE": "",
            "OPTION 2 NAME": "",
            "OPTION 2 VALUE": "",
            "OPTION 3 NAME": "",
            "OPTION 3 VALUE": "",
        }
    )
    return row, ()


def _required_field_messages(
    product: CanonicalProduct,
    offer: SourceOffer,
) -> tuple[ValidationMessage, ...]:
    missing: list[str] = []
    invalid: list[tuple[str, str]] = []
    if not _text(product.identity.canonical_sku):
        missing.append("SKU")
    if not _text(product.details.name):
        missing.append("NAME")
    if offer.pricing.calculated_price is None:
        missing.append("PRICE")
    if offer.inventory.quantity is None:
        missing.append("ON-HAND QUANTITY")

    product_type = _text(product.details.product_type) or "PHYSICAL"
    if product_type.upper() not in SUPPORTED_PRODUCT_TYPES:
        invalid.append(("TYPE", product_type))

    status = _text(product.details.status) or "ACTIVE"
    if status.upper() not in SUPPORTED_STATUSES:
        invalid.append(("STATUS", status))

    missing_messages = [
        ValidationMessage.warning(
            "godaddy_missing_required_field",
            f"Product {product.identity.canonical_sku} is missing required GoDaddy field {field} and was skipped.",
            field,
        )
        for field in missing
    ]
    invalid_messages = [
        ValidationMessage.warning(
            "godaddy_invalid_field_value",
            f"Product {product.identity.canonical_sku} has unsupported GoDaddy field {field}={value} and was skipped.",
            field,
        )
        for field, value in invalid
    ]
    return tuple(missing_messages + invalid_messages)


def _write_batches(
    rows: list[dict[str, str]],
    output_dir: Path,
    batch_size: int,
    filename_prefix: str,
) -> Iterable[ExportedFile]:
    for index, start in enumerate(range(0, len(rows), batch_size), start=1):
        batch_rows = rows[start : start + batch_size]
        path = output_dir / f"{filename_prefix}-{index:03d}.csv"
        with path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=GODADDY_COLUMNS)
            writer.writeheader()
            writer.writerows(batch_rows)
        yield ExportedFile(path=path, row_count=len(batch_rows))


def _description(
    product: CanonicalProduct,
    offer: SourceOffer,
    configuration: RunConfiguration,
) -> str:
    parts = [_text(product.details.description)]
    existing_lines = {line.strip() for line in parts[0].splitlines() if line.strip()} if parts[0] else set()
    for note in offer.compliance.description_notes(configuration.compliance):
        if note not in existing_lines:
            parts.append(note)
            existing_lines.add(note)
    return "\n\n".join(part for part in parts if part)


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _money(value: Decimal | None) -> str:
    if value is None:
        return ""
    rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return format(rounded, ".2f")


def _decimal(value: Decimal | None) -> str:
    if value is None:
        return ""
    return _strip_decimal(value)


def _strip_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal("1")))
    return format(normalized, "f")


def _bool(value: bool) -> str:
    return "true" if value else "false"


def _quantity(value: int) -> str:
    return str(value)


def _enum_text(value: object, *, default: str) -> str:
    text = _text(value)
    if not text:
        return default
    return text.upper()
