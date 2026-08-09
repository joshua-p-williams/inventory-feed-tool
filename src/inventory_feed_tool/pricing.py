from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

from inventory_feed_tool.models import (
    MapMode,
    PricingProfile,
    ProductPricing,
    RoundingMode,
    SalePriceMode,
)


@dataclass(frozen=True)
class PriceCalculation:
    calculated_price: Decimal
    pricing_reason: str


def calculate_price(
    unit_cost: Decimal,
    map_price: Decimal | None = None,
    profile: PricingProfile | None = None,
) -> PriceCalculation:
    profile = profile or PricingProfile()

    if unit_cost < 0:
        raise ValueError("unit_cost cannot be negative")

    markup_multiplier = Decimal("1") + (profile.markup_percent / Decimal("100"))
    markup_price = round_price(unit_cost * markup_multiplier, profile.rounding_mode)

    if (
        profile.map_mode == MapMode.RESPECT
        and map_price is not None
        and map_price > Decimal("0")
        and map_price > markup_price
    ):
        return PriceCalculation(
            calculated_price=round_price(map_price, profile.rounding_mode),
            pricing_reason="map_price",
        )

    return PriceCalculation(
        calculated_price=markup_price,
        pricing_reason="markup_price",
    )


def build_product_pricing(
    unit_cost: Decimal,
    profile: PricingProfile | None = None,
    msrp: Decimal | None = None,
    map_price: Decimal | None = None,
    retail_price: Decimal | None = None,
    sale_price: Decimal | None = None,
) -> ProductPricing:
    profile = profile or PricingProfile()
    calculation = calculate_price(unit_cost=unit_cost, map_price=map_price, profile=profile)
    exported_sale_price = sale_price if profile.sale_price_mode == SalePriceMode.USE_SOURCE_SALE else None
    return ProductPricing(
        unit_cost=unit_cost,
        calculated_price=calculation.calculated_price,
        msrp=msrp,
        map_price=map_price,
        retail_price=retail_price,
        sale_price=exported_sale_price,
        pricing_reason=calculation.pricing_reason,
    )


def round_price(value: Decimal, rounding_mode: RoundingMode) -> Decimal:
    if rounding_mode == RoundingMode.NEAREST_CENT:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if rounding_mode == RoundingMode.NEAREST_DOLLAR:
        return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    if rounding_mode == RoundingMode.CHARM_99:
        whole_dollars = value.quantize(Decimal("1"), rounding=ROUND_DOWN)
        candidate = whole_dollars + Decimal("0.99")
        if candidate < value:
            candidate += Decimal("1")
        return candidate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    raise ValueError(f"Unsupported rounding mode: {rounding_mode}")
