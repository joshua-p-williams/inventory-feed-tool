from __future__ import annotations

from decimal import Decimal
import unittest

from inventory_feed_tool.models import AvailabilityPolicy, AvailabilityStatus
from inventory_feed_tool.parsing import clean_optional_text, parse_availability, parse_bool, parse_money


class ParsingTests(unittest.TestCase):
    def test_clean_optional_text_returns_none_for_blank_values(self) -> None:
        self.assertIsNone(clean_optional_text("  "))
        self.assertEqual(clean_optional_text(" value "), "value")

    def test_parse_bool_accepts_common_true_values(self) -> None:
        self.assertTrue(parse_bool("yes"))
        self.assertTrue(parse_bool("1"))
        self.assertFalse(parse_bool("no"))

    def test_parse_money_accepts_currency_formatting(self) -> None:
        self.assertEqual(parse_money("$1,234.50"), Decimal("1234.50"))
        self.assertIsNone(parse_money(""))

    def test_parse_exact_available_quantity(self) -> None:
        availability = parse_availability("7")

        self.assertEqual(availability.status, AvailabilityStatus.AVAILABLE)
        self.assertEqual(availability.quantity, 7)
        self.assertTrue(availability.is_exportable_by_default)

    def test_parse_zero_quantity_is_not_exportable_by_default(self) -> None:
        availability = parse_availability("0")

        self.assertEqual(availability.status, AvailabilityStatus.OUT_OF_STOCK)
        self.assertEqual(availability.quantity, 0)
        self.assertFalse(availability.is_exportable_by_default)

    def test_parse_approximate_quantity_preserves_raw_value(self) -> None:
        availability = parse_availability("99+")

        self.assertEqual(availability.status, AvailabilityStatus.AVAILABLE)
        self.assertEqual(availability.quantity, 99)
        self.assertEqual(availability.raw_quantity, "99+")
        self.assertTrue(availability.is_exportable_by_default)

    def test_parse_approximate_quantity_uses_numeric_lower_bound_by_default(self) -> None:
        availability = parse_availability("5+")

        self.assertEqual(availability.quantity, 5)
        self.assertTrue(availability.is_exportable_by_default)

    def test_parse_approximate_quantity_can_apply_configured_floor(self) -> None:
        availability = parse_availability(
            "5+",
            policy=AvailabilityPolicy(approximate_quantity_floor=10),
        )

        self.assertEqual(availability.quantity, 10)

    def test_parse_unknown_quantity_can_be_enabled_by_policy(self) -> None:
        availability = parse_availability(
            "Call",
            policy=AvailabilityPolicy(include_unknown_quantity=True),
        )

        self.assertEqual(availability.status, AvailabilityStatus.UNKNOWN)
        self.assertTrue(availability.is_exportable_by_default)


if __name__ == "__main__":
    unittest.main()
