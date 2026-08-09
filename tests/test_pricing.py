from __future__ import annotations

from decimal import Decimal
import unittest

from inventory_feed_tool.models import MapMode, PricingProfile, RoundingMode, SalePriceMode
from inventory_feed_tool.pricing import build_product_pricing, calculate_price, round_price


class PricingTests(unittest.TestCase):
    def test_calculates_configured_markup_from_unit_cost(self) -> None:
        profile = PricingProfile(markup_percent=Decimal("20"))

        calculation = calculate_price(Decimal("100.00"), profile=profile)

        self.assertEqual(calculation.calculated_price, Decimal("120.00"))
        self.assertEqual(calculation.pricing_reason, "markup_price")

    def test_respects_map_when_markup_price_is_lower(self) -> None:
        profile = PricingProfile(markup_percent=Decimal("20"), map_mode=MapMode.RESPECT)

        calculation = calculate_price(
            Decimal("100.00"),
            map_price=Decimal("135.00"),
            profile=profile,
        )

        self.assertEqual(calculation.calculated_price, Decimal("135.00"))
        self.assertEqual(calculation.pricing_reason, "map_price")

    def test_uses_markup_when_map_is_absent(self) -> None:
        calculation = calculate_price(Decimal("100.00"), map_price=None)

        self.assertEqual(calculation.calculated_price, Decimal("125.00"))
        self.assertEqual(calculation.pricing_reason, "markup_price")

    def test_can_ignore_map_by_configuration(self) -> None:
        profile = PricingProfile(markup_percent=Decimal("20"), map_mode=MapMode.IGNORE)

        calculation = calculate_price(
            Decimal("100.00"),
            map_price=Decimal("135.00"),
            profile=profile,
        )

        self.assertEqual(calculation.calculated_price, Decimal("120.00"))
        self.assertEqual(calculation.pricing_reason, "markup_price")

    def test_ignores_source_sale_price_by_default(self) -> None:
        pricing = build_product_pricing(
            unit_cost=Decimal("100.00"),
            sale_price=Decimal("110.00"),
        )

        self.assertIsNone(pricing.sale_price)

    def test_uses_source_sale_price_when_enabled(self) -> None:
        profile = PricingProfile(sale_price_mode=SalePriceMode.USE_SOURCE_SALE)

        pricing = build_product_pricing(
            unit_cost=Decimal("100.00"),
            sale_price=Decimal("110.00"),
            profile=profile,
        )

        self.assertEqual(pricing.sale_price, Decimal("110.00"))

    def test_rounding_modes(self) -> None:
        self.assertEqual(round_price(Decimal("10.125"), RoundingMode.NEAREST_CENT), Decimal("10.13"))
        self.assertEqual(round_price(Decimal("10.50"), RoundingMode.NEAREST_DOLLAR), Decimal("11"))
        self.assertEqual(round_price(Decimal("10.50"), RoundingMode.CHARM_99), Decimal("10.99"))
        self.assertEqual(round_price(Decimal("10.99"), RoundingMode.CHARM_99), Decimal("10.99"))
        self.assertEqual(round_price(Decimal("10.991"), RoundingMode.CHARM_99), Decimal("11.99"))


if __name__ == "__main__":
    unittest.main()
