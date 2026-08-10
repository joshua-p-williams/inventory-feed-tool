from __future__ import annotations

import unittest
from decimal import Decimal

from inventory_feed_tool.aggregation import SourceSelectionOverride, aggregate_source_offers
from inventory_feed_tool.models import (
    AvailabilityStatus,
    CanonicalProduct,
    InventoryAvailability,
    ProductDetails,
    ProductIdentity,
    ProductPricing,
    RunConfiguration,
    SourceInfo,
    SourceOffer,
    SourceSelectionPolicy,
    SourceSelectionStrategy,
)
from inventory_feed_tool.validation import MessageSeverity


class AggregationTests(unittest.TestCase):
    def test_groups_offers_by_canonical_sku(self) -> None:
        first = offer("lipseys", "LIP-1", "UPC-1", upc="1")
        second = offer("davidsons", "DAV-1", "UPC-1", upc="1")
        third = offer("lipseys", "LIP-2", "UPC-2", upc="2")

        result = aggregate_source_offers([third, second, first])

        self.assertEqual(result.source_offer_count, 3)
        self.assertEqual(result.product_group_count, 2)
        self.assertEqual([product.identity.canonical_sku for product in result.products], ["UPC-1", "UPC-2"])
        self.assertEqual(len(result.products[0].offers), 2)
        self.assertIsInstance(result.products[0], CanonicalProduct)

    def test_gross_profit_strategy_selects_highest_profit_offer(self) -> None:
        low_profit = offer("lipseys", "LIP-1", "UPC-1", price="500", cost="450", quantity=10)
        high_profit = offer("davidsons", "DAV-1", "UPC-1", price="550", cost="400", quantity=1)

        result = aggregate_source_offers([low_profit, high_profit])

        self.assertEqual(result.products[0].selected_offer, high_profit)

    def test_gross_profit_tie_uses_higher_quantity(self) -> None:
        low_quantity = offer("lipseys", "LIP-1", "UPC-1", price="500", cost="400", quantity=1)
        high_quantity = offer("davidsons", "DAV-1", "UPC-1", price="600", cost="500", quantity=7)

        result = aggregate_source_offers([low_quantity, high_quantity])

        self.assertEqual(result.products[0].selected_offer, high_quantity)

    def test_quantity_strategy_selects_highest_quantity_offer(self) -> None:
        high_profit = offer("lipseys", "LIP-1", "UPC-1", price="650", cost="400", quantity=1)
        high_quantity = offer("davidsons", "DAV-1", "UPC-1", price="500", cost="400", quantity=6)
        configuration = RunConfiguration(
            source_selection=SourceSelectionPolicy(strategy=SourceSelectionStrategy.QUANTITY)
        )

        result = aggregate_source_offers([high_profit, high_quantity], configuration)

        self.assertEqual(result.products[0].selected_offer, high_quantity)

    def test_distributor_priority_strategy_uses_configured_order(self) -> None:
        lipseys_offer = offer("lipseys", "LIP-1", "UPC-1", price="650", cost="400", quantity=10)
        davidsons_offer = offer("davidsons", "DAV-1", "UPC-1", price="500", cost="400", quantity=1)
        configuration = RunConfiguration(
            source_selection=SourceSelectionPolicy(
                strategy=SourceSelectionStrategy.DISTRIBUTOR_PRIORITY,
                preferred_distributors=("davidsons", "lipseys"),
            )
        )

        result = aggregate_source_offers([lipseys_offer, davidsons_offer], configuration)

        self.assertEqual(result.products[0].selected_offer, davidsons_offer)

    def test_tie_breaker_is_deterministic_by_source_display_name(self) -> None:
        second = offer("lipseys", "B", "UPC-1", price="500", cost="400", quantity=1)
        first = offer("davidsons", "A", "UPC-1", price="500", cost="400", quantity=1)

        result = aggregate_source_offers([second, first])

        self.assertEqual(result.products[0].selected_offer, first)

    def test_tie_breaker_is_stable_when_source_names_only_differ_by_case(self) -> None:
        lowercase = offer("alpha", "sku", "UPC-1", price="500", cost="400", quantity=1)
        uppercase = offer("Alpha", "SKU", "UPC-1", price="500", cost="400", quantity=1)

        first_result = aggregate_source_offers([lowercase, uppercase])
        second_result = aggregate_source_offers([uppercase, lowercase])

        self.assertEqual(first_result.products[0].selected_offer, uppercase)
        self.assertEqual(second_result.products[0].selected_offer, uppercase)

    def test_non_exportable_offers_are_excluded_when_exportable_alternative_exists(self) -> None:
        unavailable = offer("lipseys", "LIP-1", "UPC-1", price="700", cost="100", exportable=False)
        available = offer("davidsons", "DAV-1", "UPC-1", price="500", cost="400", quantity=1)

        result = aggregate_source_offers([unavailable, available])

        self.assertEqual(result.product_groups_dropped, 0)
        self.assertEqual(result.products[0].selected_offer, available)
        self.assertEqual(len(result.products[0].offers), 2)

    def test_all_non_exportable_group_is_dropped_with_warning(self) -> None:
        unavailable = offer("lipseys", "LIP-1", "UPC-1", exportable=False)

        result = aggregate_source_offers([unavailable])

        self.assertEqual(result.products, ())
        self.assertEqual(result.product_groups_dropped, 1)
        self.assertTrue(any(message.code == "no_exportable_offer" for message in result.messages))

    def test_manual_override_selects_matching_exportable_offer(self) -> None:
        automatic_winner = offer("lipseys", "LIP-1", "UPC-1", price="700", cost="100")
        override_winner = offer("davidsons", "DAV-1", "UPC-1", price="500", cost="400")

        result = aggregate_source_offers(
            [automatic_winner, override_winner],
            overrides=(SourceSelectionOverride("UPC-1", preferred_distributor="davidsons"),),
        )

        self.assertEqual(result.products[0].selected_offer, override_winner)

    def test_manual_override_can_match_source_sku_without_distributor(self) -> None:
        automatic_winner = offer("lipseys", "LIP-1", "UPC-1", price="700", cost="100")
        override_winner = offer("davidsons", "DAV-1", "UPC-1", price="500", cost="400")

        result = aggregate_source_offers(
            [automatic_winner, override_winner],
            overrides=(SourceSelectionOverride("UPC-1", preferred_source_sku="DAV-1"),),
        )

        self.assertEqual(result.products[0].selected_offer, override_winner)

    def test_stale_manual_override_warns_and_falls_back(self) -> None:
        automatic_winner = offer("lipseys", "LIP-1", "UPC-1", price="700", cost="100")
        other = offer("davidsons", "DAV-1", "UPC-1", price="500", cost="400")

        result = aggregate_source_offers(
            [automatic_winner, other],
            overrides=(SourceSelectionOverride("UPC-1", preferred_distributor="missing"),),
        )

        self.assertEqual(result.products[0].selected_offer, automatic_winner)
        self.assertTrue(any(message.code == "source_override_not_found" for message in result.products[0].warnings))

    def test_manual_overrides_disabled_warns_and_falls_back(self) -> None:
        automatic_winner = offer("lipseys", "LIP-1", "UPC-1", price="700", cost="100")
        override_winner = offer("davidsons", "DAV-1", "UPC-1", price="500", cost="400")
        configuration = RunConfiguration(
            source_selection=SourceSelectionPolicy(allow_manual_overrides=False)
        )

        result = aggregate_source_offers(
            [automatic_winner, override_winner],
            configuration,
            overrides=(SourceSelectionOverride("UPC-1", preferred_distributor="davidsons"),),
        )

        self.assertEqual(result.products[0].selected_offer, automatic_winner)
        self.assertTrue(any(message.code == "source_override_disabled" for message in result.products[0].warnings))

    def test_override_does_not_select_non_exportable_offer(self) -> None:
        automatic_winner = offer("lipseys", "LIP-1", "UPC-1", price="500", cost="400")
        unavailable = offer("davidsons", "DAV-1", "UPC-1", price="700", cost="100", exportable=False)

        result = aggregate_source_offers(
            [automatic_winner, unavailable],
            overrides=(SourceSelectionOverride("UPC-1", preferred_distributor="davidsons"),),
        )

        self.assertEqual(result.products[0].selected_offer, automatic_winner)
        self.assertTrue(any(message.code == "source_override_not_found" for message in result.products[0].warnings))

    def test_conflicts_are_reported_for_differing_nonblank_fields(self) -> None:
        first = offer(
            "lipseys",
            "LIP-1",
            "UPC-1",
            manufacturer="Maker A",
            brand="Brand A",
            model_number="M1",
            model_name="Model One",
            name="Product A",
            category="Firearm",
            map_price="500",
        )
        second = offer(
            "davidsons",
            "DAV-1",
            "UPC-1",
            manufacturer="Maker B",
            brand="Brand B",
            model_number="M2",
            model_name="Model Two",
            name="Product B",
            category="Accessory",
            map_price="550",
        )

        result = aggregate_source_offers([first, second])
        conflicts = result.products[0].conflicts

        self.assertEqual({conflict.field for conflict in conflicts}, {
            "identity.manufacturer",
            "identity.brand",
            "identity.model_number",
            "identity.model_name",
            "details.name",
            "details.category",
            "pricing.map_price",
        })
        self.assertTrue(all(conflict.severity == MessageSeverity.WARNING for conflict in conflicts))

    def test_blank_map_price_does_not_conflict_with_nonblank_map_price(self) -> None:
        first = offer("lipseys", "LIP-1", "UPC-1", map_price=None)
        second = offer("davidsons", "DAV-1", "UPC-1", map_price="550")

        result = aggregate_source_offers([first, second])

        self.assertFalse(any(conflict.field == "pricing.map_price" for conflict in result.products[0].conflicts))

    def test_representative_fields_prefer_selected_offer(self) -> None:
        selected = offer(
            "lipseys",
            "LIP-1",
            "UPC-1",
            price="700",
            cost="100",
            manufacturer="Selected Maker",
            brand="Selected Brand",
            model_number="Selected Model Number",
            model_name="Selected Model",
            name="Selected Name",
            description="Selected Description",
            category="Selected Category",
            family="Selected Family",
        )
        unselected = offer(
            "davidsons",
            "DAV-1",
            "UPC-1",
            price="500",
            cost="400",
            manufacturer="Other Maker",
            name="Other Name",
            category="Other Category",
        )

        result = aggregate_source_offers([unselected, selected])
        product = result.products[0]

        self.assertEqual(product.identity.manufacturer, "Selected Maker")
        self.assertEqual(product.identity.brand, "Selected Brand")
        self.assertEqual(product.identity.model_number, "Selected Model Number")
        self.assertEqual(product.identity.model_name, "Selected Model")
        self.assertEqual(product.details.name, "Selected Name")
        self.assertEqual(product.details.description, "Selected Description")
        self.assertEqual(product.details.category, "Selected Category")
        self.assertEqual(product.details.family, "Selected Family")


def offer(
    distributor: str,
    source_sku: str,
    canonical_sku: str,
    *,
    upc: str | None = None,
    manufacturer: str | None = "Sample Maker",
    brand: str | None = "Sample Brand",
    model_number: str | None = "Sample Model Number",
    model_name: str | None = "Sample Model",
    name: str = "Sample Product",
    description: str = "Sample Description",
    category: str | None = "Sample Category",
    family: str | None = "Sample Family",
    price: str = "500",
    cost: str = "400",
    map_price: str | None = "450",
    quantity: int = 1,
    exportable: bool = True,
) -> SourceOffer:
    return SourceOffer(
        source=SourceInfo(distributor=distributor, source_sku=source_sku),
        identity=ProductIdentity(
            canonical_sku=canonical_sku,
            upc=upc,
            manufacturer=manufacturer,
            brand=brand,
            model_number=model_number,
            model_name=model_name,
        ),
        details=ProductDetails(
            name=name,
            description=description,
            category=category,
            family=family,
        ),
        pricing=ProductPricing(
            unit_cost=Decimal(cost),
            calculated_price=Decimal(price),
            map_price=Decimal(map_price) if map_price is not None else None,
        ),
        inventory=InventoryAvailability(
            status=AvailabilityStatus.AVAILABLE if exportable else AvailabilityStatus.OUT_OF_STOCK,
            quantity=quantity if exportable else 0,
            is_exportable_by_default=exportable,
        ),
    )


if __name__ == "__main__":
    unittest.main()
