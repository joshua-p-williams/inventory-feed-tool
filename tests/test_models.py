from __future__ import annotations

from decimal import Decimal
import unittest

from inventory_feed_tool.models import (
    AvailabilityPolicy,
    ComplianceBehavior,
    ComplianceFlags,
    CompliancePolicy,
    ExportMode,
    MapMode,
    PricingProfile,
    ProductDetails,
    ProductIdentity,
    ProductPricing,
    RunConfiguration,
    SourceInfo,
    SourceOffer,
    canonical_sku_from_upc,
    fallback_canonical_sku,
)
from inventory_feed_tool.parsing import parse_availability


class ModelTests(unittest.TestCase):
    def test_default_run_configuration_matches_mvp_decisions(self) -> None:
        configuration = RunConfiguration()

        self.assertEqual(configuration.export_mode, ExportMode.NEW)
        self.assertEqual(configuration.pricing.markup_percent, Decimal("25"))
        self.assertEqual(configuration.pricing.map_mode, MapMode.RESPECT)
        self.assertFalse(configuration.availability.include_allocated)
        self.assertFalse(configuration.availability.include_unknown_quantity)
        self.assertEqual(configuration.availability.approximate_quantity_floor, 0)
        self.assertFalse(configuration.availability.allow_backorder)
        self.assertTrue(configuration.images.include_image_urls)

    def test_upc_based_canonical_sku_removes_formatting(self) -> None:
        self.assertEqual(canonical_sku_from_upc(" 7-36676-03701-8 "), "UPC-736676037018")

    def test_fallback_canonical_sku_uses_distributor_prefix(self) -> None:
        self.assertEqual(fallback_canonical_sku("davidsons", "pdss2028"), "DAV-PDSS2028")

    def test_compliance_flags_create_description_notes_by_default(self) -> None:
        flags = ComplianceFlags(ffl_required=True, sot_required=True, nfa_item=True)

        self.assertEqual(
            flags.description_notes(),
            ("FFL required.", "SOT required.", "NFA item."),
        )

    def test_compliance_flags_can_ignore_notes_by_policy(self) -> None:
        flags = ComplianceFlags(ffl_required=True, sot_required=True)
        policy = CompliancePolicy(
            ffl_required_behavior=ComplianceBehavior.IGNORE,
            sot_required_behavior=ComplianceBehavior.DESCRIPTION_NOTE,
        )

        self.assertEqual(flags.description_notes(policy), ("SOT required.",))

    def test_canonical_product_requires_selected_offer_to_be_present(self) -> None:
        from inventory_feed_tool.models import CanonicalProduct

        first_offer = self._source_offer("lipseys", "LIP-1")
        second_offer = self._source_offer("davidsons", "DAV-1")

        with self.assertRaises(ValueError):
            CanonicalProduct(
                identity=first_offer.identity,
                details=first_offer.details,
                offers=(first_offer,),
                selected_offer=second_offer,
            )

    def test_allocated_inventory_is_preserved_but_not_exportable_by_default(self) -> None:
        availability = parse_availability("A*")

        self.assertEqual(availability.quantity, 0)
        self.assertFalse(availability.is_exportable_by_default)
        self.assertIn("Allocated", availability.availability_note)

    def test_allocated_inventory_can_be_included_by_policy(self) -> None:
        availability = parse_availability(
            "A*",
            policy=AvailabilityPolicy(include_allocated=True),
        )

        self.assertTrue(availability.is_exportable_by_default)

    def _source_offer(self, distributor: str, source_sku: str) -> SourceOffer:
        identity = ProductIdentity(canonical_sku="UPC-736676037018", upc="736676037018")
        return SourceOffer(
            source=SourceInfo(distributor=distributor, source_sku=source_sku),
            identity=identity,
            details=ProductDetails(name="Sample Product"),
            pricing=ProductPricing(
                unit_cost=Decimal("400.00"),
                calculated_price=Decimal("500.00"),
            ),
            inventory=parse_availability("2"),
        )


if __name__ == "__main__":
    unittest.main()
