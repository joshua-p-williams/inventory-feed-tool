from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from inventory_feed_tool.feeds.base import (
    FeedParseResult,
    basic_description,
    first_text,
    missing_columns,
    read_csv_rows,
    row_message,
    row_text,
    source_attributes,
)
from inventory_feed_tool.models import (
    AvailabilityStatus,
    ComplianceFlags,
    InventoryAvailability,
    ProductDetails,
    ProductIdentity,
    ProductMedia,
    RunConfiguration,
    ShippingDetails,
    SourceInfo,
    SourceOffer,
    canonical_sku_from_upc,
    fallback_canonical_sku,
)
from inventory_feed_tool.parsing import parse_availability, parse_money
from inventory_feed_tool.pricing import build_product_pricing
from inventory_feed_tool.validation import ValidationMessage


DISTRIBUTOR = "davidsons"

INVENTORY_REQUIRED_COLUMNS = {
    "Item #",
    "Item Description",
    "Dealer Price",
    "Quantity",
    "UPC Code",
    "Manufacturer",
}

QUANTITY_REQUIRED_COLUMNS = {
    "Item_Number",
    "UPC_Code",
    "Quantity_NC",
    "Quantity_AZ",
}

INVENTORY_MAPPED_COLUMNS = {
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
}

DESCRIPTION_ATTRIBUTE_COLUMNS = (
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


def parse_davidsons_inventory_csv(
    inventory_path: Path,
    configuration: RunConfiguration | None = None,
    quantity_path: Path | None = None,
) -> FeedParseResult:
    configuration = configuration or RunConfiguration()
    inventory_rows, inventory_fieldnames = read_csv_rows(inventory_path)
    missing = missing_columns(inventory_fieldnames, INVENTORY_REQUIRED_COLUMNS)
    if missing:
        return FeedParseResult(
            distributor=DISTRIBUTOR,
            source_files=_source_files(inventory_path, quantity_path),
            offers=(),
            messages=(
                ValidationMessage.error(
                    "davidsons_missing_columns",
                    f"Davidsons inventory feed is missing required columns: {', '.join(missing)}.",
                ),
            ),
            rows_seen=0,
            rows_skipped=0,
        )

    quantity_index: dict[str, dict[str, str]] | None = None
    messages: list[ValidationMessage] = []
    if quantity_path is not None:
        quantity_index_result, quantity_messages = _read_quantity_index(quantity_path)
        messages.extend(quantity_messages)
        if not any(message.severity == "error" for message in quantity_messages):
            quantity_index = quantity_index_result

    offers: list[SourceOffer] = []
    rows_skipped = 0
    for index, row in enumerate(inventory_rows, start=2):
        offer, row_messages = _parse_davidsons_row(
            row,
            inventory_path,
            index,
            configuration,
            quantity_index=quantity_index,
        )
        messages.extend(row_messages)
        if offer is None:
            rows_skipped += 1
        else:
            offers.append(offer)

    return FeedParseResult(
        distributor=DISTRIBUTOR,
        source_files=_source_files(inventory_path, quantity_path),
        offers=tuple(offers),
        messages=tuple(messages),
        rows_seen=len(inventory_rows),
        rows_skipped=rows_skipped,
    )


def _read_quantity_index(path: Path) -> tuple[dict[str, dict[str, str]], tuple[ValidationMessage, ...]]:
    rows, fieldnames = read_csv_rows(path)
    missing = missing_columns(fieldnames, QUANTITY_REQUIRED_COLUMNS)
    if missing:
        return {}, (
            ValidationMessage.error(
                "davidsons_quantity_missing_columns",
                f"Davidsons quantity feed is missing required columns: {', '.join(missing)}.",
            ),
        )

    indexed: dict[str, dict[str, str]] = {}
    messages: list[ValidationMessage] = []
    for index, row in enumerate(rows, start=2):
        item_number = row_text(row, "Item_Number")
        if item_number is None:
            messages.append(
                row_message(
                    "warning",
                    "davidsons_quantity_missing_item_number",
                    "Davidsons quantity row is missing Item_Number.",
                    row_number=index,
                    field="Item_Number",
                )
            )
            continue
        indexed[item_number] = row
    return indexed, tuple(messages)


def _parse_davidsons_row(
    row: dict[str, str],
    path: Path,
    row_number: int,
    configuration: RunConfiguration,
    *,
    quantity_index: dict[str, dict[str, str]] | None,
) -> tuple[SourceOffer | None, tuple[ValidationMessage, ...]]:
    messages: list[ValidationMessage] = []
    source_sku = row_text(row, "Item #")
    name = row_text(row, "Item Description")
    upc = row_text(row, "UPC Code")

    if source_sku is None:
        return None, (
            row_message(
                "error",
                "davidsons_missing_source_sku",
                "Davidsons row is missing Item #.",
                row_number=row_number,
                field="Item #",
            ),
        )

    if name is None:
        return None, (
            row_message(
                "error",
                "davidsons_missing_name",
                "Davidsons row is missing Item Description.",
                row_number=row_number,
                field="Item Description",
            ),
        )

    try:
        unit_cost = parse_money(row.get("Dealer Price"))
    except ValueError:
        unit_cost = None
    if unit_cost is None:
        return None, (
            row_message(
                "error",
                "davidsons_missing_unit_cost",
                "Davidsons row is missing valid Dealer Price.",
                row_number=row_number,
                field="Dealer Price",
            ),
        )

    canonical_sku = _canonical_sku(upc, source_sku, row_number, messages)

    inventory = _parse_inventory(row, source_sku, row_number, quantity_index, configuration, messages)
    map_price = _optional_positive_money(row_text(row, "MSP"), messages, row_number, "MSP")
    retail_price = _optional_positive_money(row_text(row, "Retail Price"), messages, row_number, "Retail Price")
    sale_price = _optional_positive_money(row_text(row, "Sale Price"), messages, row_number, "Sale Price")
    pricing = build_product_pricing(
        unit_cost=unit_cost,
        profile=configuration.pricing,
        msrp=retail_price,
        map_price=map_price,
        retail_price=retail_price,
        sale_price=sale_price,
    )
    attribute_subset = {
        column: value
        for column in DESCRIPTION_ATTRIBUTE_COLUMNS
        if (value := row_text(row, column)) is not None
    }
    attributes = source_attributes(row, INVENTORY_MAPPED_COLUMNS)
    for metadata_column in ("Sale Price", "Sale Ends", "Gun Type", "Model Series"):
        value = row_text(row, metadata_column)
        if value is not None:
            attributes[metadata_column] = value

    return (
        SourceOffer(
            source=SourceInfo(
                distributor=DISTRIBUTOR,
                source_file=str(path),
                source_sku=source_sku,
                source_row_number=row_number,
            ),
            identity=ProductIdentity(
                canonical_sku=canonical_sku,
                upc=upc,
                manufacturer=row_text(row, "Manufacturer"),
                brand=row_text(row, "Manufacturer"),
                model_number=source_sku,
                model_name=row_text(row, "Model Series"),
            ),
            details=ProductDetails(
                name=name,
                description=basic_description(name, attributes=attribute_subset),
                category=row_text(row, "Gun Type"),
                family=row_text(row, "Model Series"),
            ),
            pricing=pricing,
            inventory=inventory,
            shipping=ShippingDetails(),
            compliance=ComplianceFlags(),
            media=ProductMedia(),
            attributes=attributes,
            warnings=tuple(messages),
        ),
        tuple(messages),
    )


def _parse_inventory(
    row: dict[str, str],
    source_sku: str,
    row_number: int,
    quantity_index: dict[str, dict[str, str]] | None,
    configuration: RunConfiguration,
    messages: list[ValidationMessage],
) -> InventoryAvailability:
    if quantity_index is None:
        return _parse_availability(
            row_text(row, "Quantity"),
            configuration,
            messages,
            row_number,
            "Quantity",
        )

    quantity_row = quantity_index.get(source_sku)
    if quantity_row is None:
        messages.append(
            row_message(
                "warning",
                "davidsons_missing_quantity_match",
                "Davidsons quantity file has no matching row; using inventory Quantity.",
                row_number=row_number,
                field="Item #",
            )
        )
        return _parse_availability(
            row_text(row, "Quantity"),
            configuration,
            messages,
            row_number,
            "Quantity",
        )

    warehouse_values = (
        row_text(quantity_row, "Quantity_NC"),
        row_text(quantity_row, "Quantity_AZ"),
    )
    warehouse_availability = [
        _parse_availability(value, configuration, messages, row_number, field)
        for value, field in (
            (warehouse_values[0], "Quantity_NC"),
            (warehouse_values[1], "Quantity_AZ"),
        )
    ]
    available_quantity = sum(
        availability.quantity
        for availability in warehouse_availability
        if availability.status == AvailabilityStatus.AVAILABLE
    )

    raw_quantity = "/".join(value or "" for value in warehouse_values)
    if available_quantity > 0:
        note = "Merged Davidsons warehouse quantities."
        if any(availability.availability_note for availability in warehouse_availability):
            note += " One or more warehouse quantities were approximate."
        return InventoryAvailability(
            status=AvailabilityStatus.AVAILABLE,
            quantity=available_quantity,
            raw_quantity=raw_quantity,
            track_inventory=True,
            allow_backorder=configuration.availability.allow_backorder,
            availability_note=note,
            is_exportable_by_default=True,
        )

    if any(availability.status == AvailabilityStatus.ALLOCATED for availability in warehouse_availability):
        allocated = parse_availability("A*", policy=configuration.availability)
        return replace(allocated, raw_quantity=raw_quantity)

    if any(availability.status == AvailabilityStatus.UNKNOWN for availability in warehouse_availability):
        unknown = parse_availability(None, policy=configuration.availability)
        return replace(unknown, raw_quantity=raw_quantity)

    return parse_availability("0", policy=configuration.availability)


def _optional_positive_money(
    value: str | None,
    messages: list[ValidationMessage],
    row_number: int,
    field: str,
) -> Decimal | None:
    try:
        parsed = parse_money(value)
    except ValueError:
        messages.append(
            row_message(
                "warning",
                "davidsons_invalid_optional_number",
                f"Davidsons row has an invalid optional numeric value in {field}; leaving it blank.",
                row_number=row_number,
                field=field,
            )
        )
        return None
    if parsed is None or parsed <= 0:
        return None
    return parsed


def _canonical_sku(
    upc: str | None,
    source_sku: str,
    row_number: int,
    messages: list[ValidationMessage],
) -> str:
    if upc is None:
        messages.append(
            row_message(
                "warning",
                "davidsons_missing_upc",
                "Davidsons row is missing UPC Code; using source SKU fallback.",
                row_number=row_number,
                field="UPC Code",
            )
        )
        return fallback_canonical_sku(DISTRIBUTOR, source_sku)

    try:
        return canonical_sku_from_upc(upc)
    except ValueError:
        messages.append(
            row_message(
                "warning",
                "davidsons_invalid_upc",
                "Davidsons row has an invalid UPC Code; using source SKU fallback.",
                row_number=row_number,
                field="UPC Code",
            )
        )
        return fallback_canonical_sku(DISTRIBUTOR, source_sku)


def _parse_availability(
    raw_quantity: str | None,
    configuration: RunConfiguration,
    messages: list[ValidationMessage],
    row_number: int,
    field: str,
) -> InventoryAvailability:
    try:
        availability = parse_availability(raw_quantity, policy=configuration.availability)
    except ValueError:
        messages.append(
            row_message(
                "warning",
                "davidsons_invalid_quantity",
                f"Davidsons row has an invalid quantity in {field}; treating quantity as unknown.",
                row_number=row_number,
                field=field,
            )
        )
        return parse_availability(None, policy=configuration.availability)

    if availability.availability_note == "Approximate quantity.":
        messages.append(
            row_message(
                "warning",
                "davidsons_approximate_quantity",
                f"Davidsons row has an approximate quantity in {field}.",
                row_number=row_number,
                field=field,
            )
        )
    return availability


def _source_files(inventory_path: Path, quantity_path: Path | None) -> tuple[str, ...]:
    if quantity_path is None:
        return (str(inventory_path),)
    return (str(inventory_path), str(quantity_path))
