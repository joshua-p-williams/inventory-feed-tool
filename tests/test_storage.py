from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from inventory_feed_tool.models import (
    AvailabilityPolicy,
    ExportMode,
    MapMode,
    PricingProfile,
    ProductDetails,
    ProductIdentity,
    ProductPricing,
    RunConfiguration,
    SourceInfo,
    SourceOffer,
    SourceSelectionPolicy,
    SourceSelectionStrategy,
)
from inventory_feed_tool.parsing import parse_availability
from inventory_feed_tool.storage import (
    DEFAULT_TARGET_SYSTEM,
    SCHEMA_VERSION,
    LocalStore,
    connect_database,
    default_database_path,
    initialize_database,
    run_configuration_from_json,
    run_configuration_to_json,
    source_offer_payload,
)


class StorageTests(unittest.TestCase):
    def test_default_database_path_uses_windows_local_app_data(self) -> None:
        with patch("inventory_feed_tool.storage.platform.system", return_value="Windows"):
            with patch.dict("inventory_feed_tool.storage.os.environ", {"LOCALAPPDATA": r"C:\Users\Test\AppData\Local"}):
                path = default_database_path()

        self.assertEqual(
            path,
            Path(r"C:\Users\Test\AppData\Local") / "InventoryFeedTool" / "inventory-feed-tool.sqlite3",
        )

    def test_initialize_database_sets_schema_version_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            connection = connect_database(Path(temp_dir) / "test.sqlite3")

            initialize_database(connection)
            initialize_database(connection)

            version = connection.execute("PRAGMA user_version").fetchone()[0]
            tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            connection.close()

        self.assertEqual(version, SCHEMA_VERSION)
        self.assertIn("app_settings", tables)
        self.assertIn("export_runs", tables)
        self.assertIn("external_product_mappings", tables)
        self.assertIn("source_offers", tables)
        self.assertIn("source_overrides", tables)

    def test_initialize_database_rejects_newer_schema_version(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.execute("PRAGMA user_version = 99")

        with self.assertRaises(RuntimeError):
            initialize_database(connection)

        connection.close()

    def test_settings_round_trip(self) -> None:
        with self._store() as store:
            store.save_setting("sample", "value")

            self.assertEqual(store.load_setting("sample"), "value")
            self.assertIsNone(store.load_setting("missing"))

    def test_run_configuration_json_round_trip_preserves_values(self) -> None:
        configuration = RunConfiguration(
            export_mode=ExportMode.UPDATE,
            pricing=PricingProfile(markup_percent=Decimal("18.5"), map_mode=MapMode.IGNORE),
            availability=AvailabilityPolicy(include_allocated=True, allow_backorder=True),
            source_selection=SourceSelectionPolicy(
                strategy=SourceSelectionStrategy.DISTRIBUTOR_PRIORITY,
                preferred_distributors=("lipseys", "davidsons"),
            ),
        )

        restored = run_configuration_from_json(run_configuration_to_json(configuration))

        self.assertEqual(restored, configuration)

    def test_run_configuration_json_ignores_unknown_keys_and_uses_defaults(self) -> None:
        payload = json.dumps(
            {
                "export_mode": "new",
                "future_key": "ignored",
                "pricing": {"markup_percent": "12.5", "unknown": "ignored"},
                "availability": {"include_allocated": "false"},
            }
        )

        restored = run_configuration_from_json(payload)

        self.assertEqual(restored.export_mode, ExportMode.NEW)
        self.assertEqual(restored.pricing.markup_percent, Decimal("12.5"))
        self.assertFalse(restored.availability.include_allocated)

    def test_run_configuration_json_parses_string_booleans(self) -> None:
        payload = json.dumps(
            {
                "availability": {
                    "include_allocated": "true",
                    "include_unknown_quantity": "false",
                },
                "images": {
                    "include_image_urls": "false",
                    "validate_image_urls": "true",
                },
            }
        )

        restored = run_configuration_from_json(payload)

        self.assertTrue(restored.availability.include_allocated)
        self.assertFalse(restored.availability.include_unknown_quantity)
        self.assertFalse(restored.images.include_image_urls)
        self.assertTrue(restored.images.validate_image_urls)

    def test_store_run_configuration_round_trip(self) -> None:
        configuration = RunConfiguration(
            pricing=PricingProfile(markup_percent=Decimal("30")),
            availability=AvailabilityPolicy(include_unknown_quantity=True),
        )

        with self._store() as store:
            self.assertEqual(store.load_run_configuration(), RunConfiguration())

            store.save_run_configuration(configuration)

            self.assertEqual(store.load_run_configuration(), configuration)

    def test_create_export_run_stores_metadata(self) -> None:
        configuration = RunConfiguration(export_mode=ExportMode.UPDATE)

        with self._store() as store:
            export_run_id = store.create_export_run(
                configuration,
                output_folder="/tmp/output",
                notes="test run",
            )
            row = store.connection.execute(
                "SELECT * FROM export_runs WHERE id = ?",
                (export_run_id,),
            ).fetchone()

        self.assertEqual(row["export_mode"], "update")
        self.assertEqual(row["output_folder"], "/tmp/output")
        self.assertEqual(row["notes"], "test run")

    def test_external_product_mapping_upsert_and_find_by_sku(self) -> None:
        with self._store() as store:
            mapping = store.upsert_external_product_mapping(
                target_system=DEFAULT_TARGET_SYSTEM,
                canonical_sku="UPC-736676037018",
                upc="736676037018",
                distributor="lipseys",
                source_sku="LIP-1",
                external_product_id="GD-1",
            )

            found = store.find_external_product_mapping(
                target_system=DEFAULT_TARGET_SYSTEM,
                canonical_sku="UPC-736676037018",
            )

        self.assertEqual(mapping.external_product_id, "GD-1")
        self.assertEqual(found, mapping)

    def test_external_product_mapping_upsert_updates_existing_row(self) -> None:
        with self._store() as store:
            first = store.upsert_external_product_mapping(
                target_system=DEFAULT_TARGET_SYSTEM,
                canonical_sku="UPC-736676037018",
                external_product_id="GD-1",
            )
            second = store.upsert_external_product_mapping(
                target_system=DEFAULT_TARGET_SYSTEM,
                canonical_sku="UPC-736676037018",
                upc="736676037018",
                external_product_id="GD-2",
            )

        self.assertEqual(second.id, first.id)
        self.assertEqual(second.external_product_id, "GD-2")
        self.assertEqual(second.upc, "736676037018")

    def test_external_product_mapping_find_by_upc_is_scoped_to_target_system(self) -> None:
        with self._store() as store:
            store.upsert_external_product_mapping(
                target_system="godaddy",
                canonical_sku="UPC-736676037018",
                upc="736676037018",
                external_product_id="GD-1",
            )
            store.upsert_external_product_mapping(
                target_system="other",
                canonical_sku="UPC-736676037018",
                upc="736676037018",
                external_product_id="OTHER-1",
            )

            found = store.find_external_product_mapping(target_system="other", upc="736676037018")

        self.assertIsNotNone(found)
        self.assertEqual(found.external_product_id, "OTHER-1")

    def test_record_source_offer_snapshot(self) -> None:
        offer = self._source_offer()

        with self._store() as store:
            export_run_id = store.create_export_run(RunConfiguration())
            snapshot_id = store.record_source_offer_snapshot(export_run_id, offer, is_selected=True)
            row = store.connection.execute(
                "SELECT * FROM source_offers WHERE id = ?",
                (snapshot_id,),
            ).fetchone()

        self.assertEqual(row["canonical_sku"], "UPC-736676037018")
        self.assertEqual(row["unit_cost"], "400.00")
        self.assertEqual(row["calculated_price"], "500.00")
        self.assertEqual(row["quantity"], 2)
        self.assertEqual(row["is_selected"], 1)
        self.assertEqual(json.loads(row["payload_json"])["attributes"]["finish"], "blued")

    def test_source_offer_payload_contains_compact_metadata(self) -> None:
        payload = source_offer_payload(self._source_offer())

        self.assertEqual(payload["source"]["distributor"], "lipseys")
        self.assertEqual(payload["identity"]["canonical_sku"], "UPC-736676037018")
        self.assertEqual(payload["pricing"]["unit_cost"], "400.00")
        self.assertEqual(payload["attributes"]["finish"], "blued")

    def test_source_override_upsert_and_find_by_sku(self) -> None:
        with self._store() as store:
            override = store.upsert_source_override(
                target_system=DEFAULT_TARGET_SYSTEM,
                canonical_sku="UPC-736676037018",
                upc="736676037018",
                preferred_distributor="lipseys",
                preferred_source_sku="LIP-1",
            )

            found = store.find_source_override(
                target_system=DEFAULT_TARGET_SYSTEM,
                canonical_sku="UPC-736676037018",
            )

        self.assertEqual(found, override)
        self.assertEqual(found.preferred_distributor, "lipseys")

    def test_source_override_find_by_upc_is_scoped_to_target_system(self) -> None:
        with self._store() as store:
            store.upsert_source_override(
                target_system="godaddy",
                canonical_sku="UPC-736676037018",
                upc="736676037018",
                preferred_distributor="lipseys",
            )
            store.upsert_source_override(
                target_system="other",
                canonical_sku="UPC-736676037018",
                upc="736676037018",
                preferred_distributor="davidsons",
            )

            found = store.find_source_override(target_system="other", upc="736676037018")

        self.assertIsNotNone(found)
        self.assertEqual(found.preferred_distributor, "davidsons")

    def test_mapping_lookup_requires_sku_or_upc(self) -> None:
        with self._store() as store:
            with self.assertRaises(ValueError):
                store.find_external_product_mapping(target_system=DEFAULT_TARGET_SYSTEM)

    def test_mapping_upsert_requires_target_system_and_sku(self) -> None:
        with self._store() as store:
            with self.assertRaises(ValueError):
                store.upsert_external_product_mapping(
                    target_system=" ",
                    canonical_sku="UPC-736676037018",
                )
            with self.assertRaises(ValueError):
                store.upsert_external_product_mapping(
                    target_system=DEFAULT_TARGET_SYSTEM,
                    canonical_sku=" ",
                )

    def test_source_override_lookup_requires_sku_or_upc(self) -> None:
        with self._store() as store:
            with self.assertRaises(ValueError):
                store.find_source_override(target_system=DEFAULT_TARGET_SYSTEM)

    def _source_offer(self) -> SourceOffer:
        return SourceOffer(
            source=SourceInfo(distributor="lipseys", source_sku="LIP-1", source_file="feed.csv"),
            identity=ProductIdentity(
                canonical_sku="UPC-736676037018",
                upc="736676037018",
                manufacturer="Example Manufacturer",
                model_number="MODEL-1",
            ),
            details=ProductDetails(
                name="Sample Product",
                description="Sample description",
                category="Firearm",
                family="Sample Family",
            ),
            pricing=ProductPricing(
                unit_cost=Decimal("400.00"),
                calculated_price=Decimal("500.00"),
                map_price=Decimal("475.00"),
                pricing_reason="markup_price",
            ),
            inventory=parse_availability("2"),
            attributes={"finish": "blued"},
        )

    def _store(self) -> LocalStoreContext:
        return LocalStoreContext()


class LocalStoreContext:
    def __enter__(self) -> LocalStore:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = LocalStore.open(Path(self.temp_dir.name) / "test.sqlite3")
        return self.store

    def __exit__(self, *args: object) -> None:
        self.store.close()
        self.temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
