from __future__ import annotations

from decimal import Decimal, InvalidOperation

from inventory_feed_tool.models import (
    AvailabilityPolicy,
    AvailabilityStatus,
    InventoryAvailability,
)


ALLOCATED_TOKENS = {"A", "A*", "ALLOCATED"}
UNKNOWN_TOKENS = {"CALL", "N/A", "NA", "UNKNOWN", "TBD"}


def clean_optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_bool(value: object) -> bool:
    text = str(value).strip().lower()
    return text in {"1", "true", "t", "yes", "y"}


def parse_money(value: object) -> Decimal | None:
    text = clean_optional_text(value)
    if text is None:
        return None

    normalized = text.replace("$", "").replace(",", "")
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid money value: {value}") from exc


def parse_availability(
    raw_quantity: object,
    *,
    allocated: bool = False,
    policy: AvailabilityPolicy | None = None,
    track_inventory: bool = True,
) -> InventoryAvailability:
    policy = policy or AvailabilityPolicy()
    raw_text = clean_optional_text(raw_quantity)
    upper_text = raw_text.upper() if raw_text is not None else ""

    if allocated or upper_text in ALLOCATED_TOKENS:
        return InventoryAvailability(
            status=AvailabilityStatus.ALLOCATED,
            quantity=0,
            raw_quantity=raw_text,
            track_inventory=track_inventory,
            allow_backorder=policy.allow_backorder,
            availability_note="Allocated inventory is not exportable by default.",
            is_exportable_by_default=policy.include_allocated,
        )

    if raw_text is None or upper_text in UNKNOWN_TOKENS:
        return InventoryAvailability(
            status=AvailabilityStatus.UNKNOWN,
            quantity=0,
            raw_quantity=raw_text,
            track_inventory=track_inventory,
            allow_backorder=policy.allow_backorder,
            availability_note="Quantity is unknown.",
            is_exportable_by_default=policy.include_unknown_quantity,
        )

    if upper_text.endswith("+"):
        quantity = _parse_quantity_number(upper_text[:-1])
        return InventoryAvailability(
            status=AvailabilityStatus.AVAILABLE if quantity > 0 else AvailabilityStatus.OUT_OF_STOCK,
            quantity=max(quantity, policy.approximate_quantity_floor),
            raw_quantity=raw_text,
            track_inventory=track_inventory,
            allow_backorder=policy.allow_backorder,
            availability_note="Approximate quantity.",
            is_exportable_by_default=quantity > 0,
        )

    quantity = _parse_quantity_number(raw_text)
    if quantity == 0:
        return InventoryAvailability(
            status=AvailabilityStatus.OUT_OF_STOCK,
            quantity=0,
            raw_quantity=raw_text,
            track_inventory=track_inventory,
            allow_backorder=policy.allow_backorder,
            availability_note="Out of stock.",
            is_exportable_by_default=policy.include_zero_quantity,
        )

    return InventoryAvailability(
        status=AvailabilityStatus.AVAILABLE,
        quantity=quantity,
        raw_quantity=raw_text,
        track_inventory=track_inventory,
        allow_backorder=policy.allow_backorder,
        availability_note="",
        is_exportable_by_default=True,
    )


def _parse_quantity_number(value: str) -> int:
    try:
        quantity = int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid quantity value: {value}") from exc

    if quantity < 0:
        raise ValueError("quantity cannot be negative")

    return quantity

