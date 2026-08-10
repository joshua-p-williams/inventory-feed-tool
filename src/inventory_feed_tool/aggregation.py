from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Iterable, TypeVar

from inventory_feed_tool.models import (
    CanonicalProduct,
    ProductDetails,
    ProductIdentity,
    RunConfiguration,
    SourceOffer,
    SourceSelectionStrategy,
)
from inventory_feed_tool.validation import ConflictMessage, MessageSeverity, ValidationMessage


@dataclass(frozen=True)
class AggregationResult:
    products: tuple[CanonicalProduct, ...]
    messages: tuple[ValidationMessage, ...] = ()
    source_offer_count: int = 0
    product_group_count: int = 0
    product_groups_dropped: int = 0


@dataclass(frozen=True)
class SourceSelectionOverride:
    canonical_sku: str
    preferred_distributor: str | None = None
    preferred_source_sku: str | None = None

    def __post_init__(self) -> None:
        if not self.canonical_sku.strip():
            raise ValueError("canonical_sku is required")


T = TypeVar("T")


def aggregate_source_offers(
    offers: Iterable[SourceOffer],
    configuration: RunConfiguration | None = None,
    overrides: Iterable[SourceSelectionOverride] = (),
) -> AggregationResult:
    configuration = configuration or RunConfiguration()
    offer_list = tuple(offers)
    override_map = _override_map(overrides)
    groups = _group_offers(offer_list)
    products: list[CanonicalProduct] = []
    messages: list[ValidationMessage] = []
    groups_dropped = 0

    for canonical_sku in sorted(groups):
        group_offers = tuple(sorted(groups[canonical_sku], key=_offer_sort_key))
        candidates = tuple(offer for offer in group_offers if offer.inventory.is_exportable_by_default)
        override = override_map.get(canonical_sku)

        if not candidates:
            groups_dropped += 1
            messages.append(
                ValidationMessage.warning(
                    "no_exportable_offer",
                    f"No exportable source offer exists for {canonical_sku}; product group was dropped.",
                    "selected_offer",
                )
            )
            continue

        selected_offer, product_warnings = _select_offer(candidates, configuration, override)
        conflicts = _detect_conflicts(group_offers)

        products.append(
            CanonicalProduct(
                identity=_representative_identity(canonical_sku, selected_offer, group_offers),
                details=_representative_details(selected_offer, group_offers),
                offers=group_offers,
                selected_offer=selected_offer,
                conflicts=conflicts,
                warnings=product_warnings,
            )
        )

    return AggregationResult(
        products=tuple(products),
        messages=tuple(messages),
        source_offer_count=len(offer_list),
        product_group_count=len(groups),
        product_groups_dropped=groups_dropped,
    )


def _group_offers(offers: Iterable[SourceOffer]) -> dict[str, list[SourceOffer]]:
    groups: dict[str, list[SourceOffer]] = defaultdict(list)
    for offer in offers:
        groups[offer.identity.canonical_sku].append(offer)
    return dict(groups)


def _override_map(overrides: Iterable[SourceSelectionOverride]) -> dict[str, SourceSelectionOverride]:
    mapped: dict[str, SourceSelectionOverride] = {}
    for override in overrides:
        mapped.setdefault(override.canonical_sku, override)
    return mapped


def _select_offer(
    candidates: tuple[SourceOffer, ...],
    configuration: RunConfiguration,
    override: SourceSelectionOverride | None,
) -> tuple[SourceOffer, tuple[ValidationMessage, ...]]:
    messages: list[ValidationMessage] = []
    if override is not None:
        if configuration.source_selection.allow_manual_overrides:
            override_offer = _select_override(candidates, override)
            if override_offer is not None:
                return override_offer, ()
            messages.append(
                ValidationMessage.warning(
                    "source_override_not_found",
                    f"Source selection override for {override.canonical_sku} did not match an exportable offer.",
                    "selected_offer",
                )
            )
        else:
            messages.append(
                ValidationMessage.warning(
                    "source_override_disabled",
                    f"Source selection override for {override.canonical_sku} was ignored because overrides are disabled.",
                    "selected_offer",
                )
            )

    return _select_automatic(candidates, configuration), tuple(messages)


def _select_override(
    candidates: tuple[SourceOffer, ...],
    override: SourceSelectionOverride,
) -> SourceOffer | None:
    distributor = _normalize(override.preferred_distributor)
    source_sku = _normalize(override.preferred_source_sku)
    if distributor is None and source_sku is None:
        return None

    matches = []
    for offer in candidates:
        distributor_matches = distributor is None or _normalize(offer.source.distributor) == distributor
        source_sku_matches = source_sku is None or _normalize(offer.source.source_sku) == source_sku
        if distributor_matches and source_sku_matches:
            matches.append(offer)

    if not matches:
        return None
    return sorted(matches, key=_offer_sort_key)[0]


def _select_automatic(candidates: tuple[SourceOffer, ...], configuration: RunConfiguration) -> SourceOffer:
    strategy = configuration.source_selection.strategy
    priority = _distributor_priority(configuration.source_selection.preferred_distributors)

    if strategy == SourceSelectionStrategy.QUANTITY:
        return sorted(candidates, key=lambda offer: _quantity_sort_key(offer, priority))[0]
    if strategy == SourceSelectionStrategy.DISTRIBUTOR_PRIORITY:
        return sorted(candidates, key=lambda offer: _priority_sort_key(offer, priority))[0]
    return sorted(candidates, key=lambda offer: _gross_profit_sort_key(offer, priority))[0]


def _gross_profit_sort_key(offer: SourceOffer, priority: dict[str, int]) -> tuple[Decimal, int, int, str, str]:
    return (
        -_gross_profit(offer),
        -offer.inventory.quantity,
        _priority_index(offer, priority),
        *_source_tie_breaker(offer),
    )


def _quantity_sort_key(offer: SourceOffer, priority: dict[str, int]) -> tuple[int, Decimal, int, str, str]:
    return (
        -offer.inventory.quantity,
        -_gross_profit(offer),
        _priority_index(offer, priority),
        *_source_tie_breaker(offer),
    )


def _priority_sort_key(offer: SourceOffer, priority: dict[str, int]) -> tuple[int, Decimal, int, str, str]:
    return (
        _priority_index(offer, priority),
        -_gross_profit(offer),
        -offer.inventory.quantity,
        *_source_tie_breaker(offer),
    )


def _gross_profit(offer: SourceOffer) -> Decimal:
    return offer.pricing.calculated_price - offer.pricing.unit_cost


def _distributor_priority(distributors: tuple[str, ...]) -> dict[str, int]:
    priority: dict[str, int] = {}
    for index, distributor in enumerate(distributors):
        normalized = _normalize(distributor)
        if normalized is not None:
            priority.setdefault(normalized, index)
    return priority


def _priority_index(offer: SourceOffer, priority: dict[str, int]) -> int:
    normalized = _normalize(offer.source.distributor)
    return priority.get(normalized or "", len(priority) + 1)


def _offer_sort_key(offer: SourceOffer) -> tuple[str, str, str, str]:
    return (
        offer.identity.canonical_sku,
        _normalize(offer.source.distributor) or "",
        _normalize(offer.source.source_sku) or "",
        offer.source.display_name,
    )


def _source_tie_breaker(offer: SourceOffer) -> tuple[str, str]:
    return (offer.source.display_name.lower(), offer.source.display_name)


def _representative_identity(
    canonical_sku: str,
    selected_offer: SourceOffer,
    offers: tuple[SourceOffer, ...],
) -> ProductIdentity:
    return ProductIdentity(
        canonical_sku=canonical_sku,
        upc=_prefer_selected(selected_offer.identity.upc, (offer.identity.upc for offer in offers)),
        ean=_prefer_selected(selected_offer.identity.ean, (offer.identity.ean for offer in offers)),
        gtin=_prefer_selected(selected_offer.identity.gtin, (offer.identity.gtin for offer in offers)),
        isbn=_prefer_selected(selected_offer.identity.isbn, (offer.identity.isbn for offer in offers)),
        manufacturer=_prefer_selected(
            selected_offer.identity.manufacturer,
            (offer.identity.manufacturer for offer in offers),
        ),
        brand=_prefer_selected(selected_offer.identity.brand, (offer.identity.brand for offer in offers)),
        model_number=_prefer_selected(
            selected_offer.identity.model_number,
            (offer.identity.model_number for offer in offers),
        ),
        model_name=_prefer_selected(selected_offer.identity.model_name, (offer.identity.model_name for offer in offers)),
    )


def _representative_details(selected_offer: SourceOffer, offers: tuple[SourceOffer, ...]) -> ProductDetails:
    return ProductDetails(
        name=_prefer_selected(selected_offer.details.name, (offer.details.name for offer in offers)) or "",
        description=_prefer_selected(
            selected_offer.details.description,
            (offer.details.description for offer in offers),
        )
        or "",
        product_type=_prefer_selected(
            selected_offer.details.product_type,
            (offer.details.product_type for offer in offers),
        )
        or "PHYSICAL",
        category=_prefer_selected(selected_offer.details.category, (offer.details.category for offer in offers)),
        family=_prefer_selected(selected_offer.details.family, (offer.details.family for offer in offers)),
        status=_prefer_selected(selected_offer.details.status, (offer.details.status for offer in offers)) or "ACTIVE",
    )


def _detect_conflicts(offers: tuple[SourceOffer, ...]) -> tuple[ConflictMessage, ...]:
    conflicts: list[ConflictMessage] = []
    string_fields: tuple[tuple[str, Callable[[SourceOffer], str | None]], ...] = (
        ("identity.manufacturer", lambda offer: offer.identity.manufacturer),
        ("identity.brand", lambda offer: offer.identity.brand),
        ("identity.model_number", lambda offer: offer.identity.model_number),
        ("identity.model_name", lambda offer: offer.identity.model_name),
        ("details.name", lambda offer: offer.details.name),
        ("details.category", lambda offer: offer.details.category),
    )

    for field, getter in string_fields:
        conflicting_offers = _string_conflict_offers(offers, getter)
        if conflicting_offers:
            conflicts.append(_conflict(field, conflicting_offers))

    map_price_conflicts = _map_price_conflict_offers(offers)
    if map_price_conflicts:
        conflicts.append(_conflict("pricing.map_price", map_price_conflicts))

    return tuple(conflicts)


def _string_conflict_offers(
    offers: tuple[SourceOffer, ...],
    getter: Callable[[SourceOffer], str | None],
) -> tuple[SourceOffer, ...]:
    values = {
        normalized
        for offer in offers
        if (normalized := _normalize(getter(offer))) is not None
    }
    if len(values) <= 1:
        return ()
    return tuple(offer for offer in offers if _normalize(getter(offer)) is not None)


def _map_price_conflict_offers(offers: tuple[SourceOffer, ...]) -> tuple[SourceOffer, ...]:
    values = {offer.pricing.map_price for offer in offers if offer.pricing.map_price is not None}
    if len(values) <= 1:
        return ()
    return tuple(offer for offer in offers if offer.pricing.map_price is not None)


def _conflict(field: str, offers: tuple[SourceOffer, ...]) -> ConflictMessage:
    return ConflictMessage(
        severity=MessageSeverity.WARNING,
        code="source_field_conflict",
        message=f"Source offers disagree on {field}.",
        field=field,
        offer_sources=tuple(offer.source.display_name for offer in offers),
    )


def _prefer_selected(selected_value: T | None, fallback_values: Iterable[T | None]) -> T | None:
    if _is_present(selected_value):
        return selected_value
    for value in fallback_values:
        if _is_present(value):
            return value
    return None


def _is_present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None
