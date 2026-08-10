from __future__ import annotations

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
from inventory_feed_tool.parsing import parse_availability, parse_bool, parse_money
from inventory_feed_tool.pricing import build_product_pricing
from inventory_feed_tool.validation import ValidationMessage


DISTRIBUTOR = "lipseys"
LIPSEYS_IMAGE_BASE_URL = "https://www.lipseyscloud.com/images/"
LIPSEYS_IMAGE_SUFFIX = "?height=320&width=480&scale=canvas"
LIPSEYS_MISSING_IMAGE = "li-missing-image.png"

REQUIRED_COLUMNS = {
    "ITEMNO",
    "DESCRIPTION1",
    "UPC",
    "MANUFACTURER",
    "CURRENTPRICE",
    "PRICE",
    "QUANTITY",
    "ALLOCATED",
}

MAPPED_COLUMNS = {
    "ITEMNO",
    "DESCRIPTION1",
    "DESCRIPTION2",
    "UPC",
    "MANUFACTURERMODELNO",
    "MSRP",
    "MODEL",
    "MANUFACTURER",
    "TYPE",
    "ITEMTYPE",
    "ITEMGROUP",
    "FAMILY",
    "PRICE",
    "CURRENTPRICE",
    "RETAILMAP",
    "QUANTITY",
    "ALLOCATED",
    "FFLREQUIRED",
    "SOTREQUIRED",
    "IMAGENAME",
    "SHIPPINGWEIGHT",
    "WEIGHT",
    "PACKAGELENGTH",
    "PACKAGEWIDTH",
    "PACKAGEHEIGHT",
    "ITEMLENGTH",
    "ITEMWIDTH",
    "ITEMHEIGHT",
}

DESCRIPTION_ATTRIBUTE_COLUMNS = (
    "CALIBERGAUGE",
    "ACTION",
    "BARRELLENGTH",
    "CAPACITY",
    "FINISH",
    "OVERALLLENGTH",
    "SIGHTS",
    "STOCKFRAMEGRIPS",
    "MAGAZINE",
    "FAMILY",
    "ITEMGROUP",
)


def parse_lipseys_csv(path: Path, configuration: RunConfiguration | None = None) -> FeedParseResult:
    configuration = configuration or RunConfiguration()
    rows, fieldnames = read_csv_rows(path)
    missing = missing_columns(fieldnames, REQUIRED_COLUMNS)
    if missing:
        return FeedParseResult(
            distributor=DISTRIBUTOR,
            source_files=(str(path),),
            offers=(),
            messages=(
                ValidationMessage.error(
                    "lipseys_missing_columns",
                    f"Lipseys feed is missing required columns: {', '.join(missing)}.",
                ),
            ),
            rows_seen=0,
            rows_skipped=0,
        )

    offers: list[SourceOffer] = []
    messages: list[ValidationMessage] = []
    rows_skipped = 0

    for index, row in enumerate(rows, start=2):
        offer, row_messages = _parse_lipseys_row(row, path, index, configuration)
        messages.extend(row_messages)
        if offer is None:
            rows_skipped += 1
        else:
            offers.append(offer)

    return FeedParseResult(
        distributor=DISTRIBUTOR,
        source_files=(str(path),),
        offers=tuple(offers),
        messages=tuple(messages),
        rows_seen=len(rows),
        rows_skipped=rows_skipped,
    )


def lipseys_image_url(image_name: str | None) -> str | None:
    if image_name is None:
        return None
    normalized = image_name.strip()
    if not normalized or normalized.lower() == LIPSEYS_MISSING_IMAGE:
        return None
    return f"{LIPSEYS_IMAGE_BASE_URL}{normalized}{LIPSEYS_IMAGE_SUFFIX}"


def _parse_lipseys_row(
    row: dict[str, str],
    path: Path,
    row_number: int,
    configuration: RunConfiguration,
) -> tuple[SourceOffer | None, tuple[ValidationMessage, ...]]:
    messages: list[ValidationMessage] = []
    source_sku = row_text(row, "ITEMNO")
    name = row_text(row, "DESCRIPTION1")
    upc = row_text(row, "UPC")

    if source_sku is None:
        return None, (
            row_message(
                "error",
                "lipseys_missing_source_sku",
                "Lipseys row is missing ITEMNO.",
                row_number=row_number,
                field="ITEMNO",
            ),
        )

    if name is None:
        return None, (
            row_message(
                "error",
                "lipseys_missing_name",
                "Lipseys row is missing DESCRIPTION1.",
                row_number=row_number,
                field="DESCRIPTION1",
            ),
        )

    unit_cost = _required_money(row, "CURRENTPRICE", "PRICE")
    if unit_cost is None:
        return None, (
            row_message(
                "error",
                "lipseys_missing_unit_cost",
                "Lipseys row is missing valid CURRENTPRICE or PRICE.",
                row_number=row_number,
                field="CURRENTPRICE",
            ),
        )

    canonical_sku = _canonical_sku(upc, source_sku, row_number, messages)

    map_price = _optional_positive_money(row_text(row, "RETAILMAP"), messages, row_number, "RETAILMAP")
    msrp = _optional_positive_money(row_text(row, "MSRP"), messages, row_number, "MSRP")
    pricing = build_product_pricing(
        unit_cost=unit_cost,
        profile=configuration.pricing,
        msrp=msrp,
        map_price=map_price,
    )
    inventory = _parse_availability(
        row_text(row, "QUANTITY"),
        configuration,
        messages,
        row_number,
        "QUANTITY",
        allocated=parse_bool(row.get("ALLOCATED")),
    )

    image_name = row_text(row, "IMAGENAME")
    image_url = lipseys_image_url(image_name)
    if image_name is None or image_url is None:
        messages.append(
            row_message(
                "warning",
                "lipseys_missing_image",
                "Lipseys row has no usable image.",
                row_number=row_number,
                field="IMAGENAME",
            )
        )

    attribute_subset = {
        column: value
        for column in DESCRIPTION_ATTRIBUTE_COLUMNS
        if (value := row_text(row, column)) is not None
    }
    description = basic_description(
        name,
        row_text(row, "DESCRIPTION2"),
        attributes=attribute_subset,
    )
    attributes = source_attributes(row, MAPPED_COLUMNS)
    for metadata_column in ("CANDROPSHIP", "ONSALE", "SPECIAL", "ITEMGROUP", "TYPE"):
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
                manufacturer=row_text(row, "MANUFACTURER"),
                brand=row_text(row, "MANUFACTURER"),
                model_number=row_text(row, "MANUFACTURERMODELNO"),
                model_name=row_text(row, "MODEL"),
            ),
            details=ProductDetails(
                name=name,
                description=description,
                category=first_text(row, "ITEMTYPE", "ITEMGROUP"),
                family=row_text(row, "FAMILY"),
            ),
            pricing=pricing,
            inventory=inventory,
            shipping=ShippingDetails(
                weight=_optional_positive_money(
                    first_text(row, "SHIPPINGWEIGHT", "WEIGHT"), messages, row_number, "SHIPPINGWEIGHT"
                ),
                length=_optional_positive_money(
                    first_text(row, "PACKAGELENGTH", "ITEMLENGTH"), messages, row_number, "PACKAGELENGTH"
                ),
                width=_optional_positive_money(
                    first_text(row, "PACKAGEWIDTH", "ITEMWIDTH"), messages, row_number, "PACKAGEWIDTH"
                ),
                height=_optional_positive_money(
                    first_text(row, "PACKAGEHEIGHT", "ITEMHEIGHT"), messages, row_number, "PACKAGEHEIGHT"
                ),
            ),
            compliance=ComplianceFlags(
                ffl_required=parse_bool(row.get("FFLREQUIRED")),
                sot_required=parse_bool(row.get("SOTREQUIRED")),
                country_of_origin=row_text(row, "COUNTRYOFORIGIN"),
            ),
            media=ProductMedia(
                image_url=image_url,
                image_name=image_name,
                image_source=DISTRIBUTOR if image_url is not None else None,
            ),
            attributes=attributes,
            warnings=tuple(messages),
        ),
        tuple(messages),
    )


def _required_money(row: dict[str, str], *columns: str) -> Decimal | None:
    for column in columns:
        try:
            value = parse_money(row.get(column))
        except ValueError:
            continue
        if value is not None:
            return value
    return None


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
                "lipseys_invalid_optional_number",
                f"Lipseys row has an invalid optional numeric value in {field}; leaving it blank.",
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
                "lipseys_missing_upc",
                "Lipseys row is missing UPC; using source SKU fallback.",
                row_number=row_number,
                field="UPC",
            )
        )
        return fallback_canonical_sku(DISTRIBUTOR, source_sku)

    try:
        return canonical_sku_from_upc(upc)
    except ValueError:
        messages.append(
            row_message(
                "warning",
                "lipseys_invalid_upc",
                "Lipseys row has an invalid UPC; using source SKU fallback.",
                row_number=row_number,
                field="UPC",
            )
        )
        return fallback_canonical_sku(DISTRIBUTOR, source_sku)


def _parse_availability(
    raw_quantity: str | None,
    configuration: RunConfiguration,
    messages: list[ValidationMessage],
    row_number: int,
    field: str,
    *,
    allocated: bool = False,
) -> InventoryAvailability:
    try:
        availability = parse_availability(raw_quantity, allocated=allocated, policy=configuration.availability)
    except ValueError:
        messages.append(
            row_message(
                "warning",
                "lipseys_invalid_quantity",
                f"Lipseys row has an invalid quantity in {field}; treating quantity as unknown.",
                row_number=row_number,
                field=field,
            )
        )
        return parse_availability(None, policy=configuration.availability)

    if availability.availability_note == "Approximate quantity.":
        messages.append(
            row_message(
                "warning",
                "lipseys_approximate_quantity",
                "Lipseys row has an approximate quantity.",
                row_number=row_number,
                field=field,
            )
        )
    return availability
