from __future__ import annotations

import csv
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from inventory_feed_tool.exporters.godaddy import GODADDY_COLUMNS, export_godaddy_csv
from inventory_feed_tool.models import (
    AvailabilityStatus,
    CanonicalProduct,
    ComplianceFlags,
    ExportMode,
    ImagePolicy,
    InventoryAvailability,
    ProductDetails,
    ProductIdentity,
    ProductMedia,
    ProductPricing,
    RunConfiguration,
    ShippingDetails,
    SourceInfo,
    SourceOffer,
)


class GoDaddyExporterTests(unittest.TestCase):
    def test_writes_valid_new_import_row_with_expected_columns(self) -> None:
        product = canonical_product()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "exports"

            result = export_godaddy_csv([product], output_dir)

            self.assertEqual(result.products_seen, 1)
            self.assertEqual(result.products_exported, 1)
            self.assertEqual(result.products_skipped, 0)
            self.assertEqual(len(result.files), 1)
            rows = self._read_csv(result.files[0].path)

        self.assertEqual(rows.fieldnames, list(GODADDY_COLUMNS))
        row = rows.rows[0]
        self.assertEqual(row["SKU"], "UPC-736676037018")
        self.assertEqual(row["UPC"], "736676037018")
        self.assertEqual(row["TYPE"], "PHYSICAL")
        self.assertEqual(row["NAME"], "Sample Product")
        self.assertEqual(row["PRODUCT ID"], "")
        self.assertEqual(row["MANUFACTURER"], "Sample Maker")
        self.assertEqual(row["MODEL NUMBER"], "MODEL-1")
        self.assertEqual(row["MSRP"], "600.00")
        self.assertEqual(row["BRAND"], "Sample Brand")
        self.assertEqual(row["STATUS"], "ACTIVE")
        self.assertEqual(row["PRICE"], "525.00")
        self.assertEqual(row["SALE PRICE"], "500.50")
        self.assertEqual(row["UNIT COST"], "400.00")
        self.assertEqual(row["ALLOW CUSTOM PRICE"], "false")
        self.assertEqual(row["ON-HAND QUANTITY"], "3")
        self.assertEqual(row["TRACK INVENTORY"], "true")
        self.assertEqual(row["ALLOW BACKORDER"], "false")
        self.assertEqual(row["DISABLE SHIPPING"], "false")
        self.assertEqual(row["FREE SHIPPING"], "true")
        self.assertEqual(row["FIXED SHIPPING FEE"], "12.30")
        self.assertEqual(row["WEIGHT"], "3.25")
        self.assertEqual(row["LENGTH"], "12")
        self.assertEqual(row["WIDTH"], "8.5")
        self.assertEqual(row["HEIGHT"], "4")
        self.assertEqual(row["IMAGE URL"], "https://example.com/product.jpg")
        self.assertEqual(row["OPTION 1 NAME"], "")
        self.assertEqual(row["OPTION 3 VALUE"], "")

    def test_batches_rows_with_configurable_batch_size(self) -> None:
        products = [
            canonical_product(canonical_sku=f"UPC-{index}", source_sku=f"SRC-{index}")
            for index in range(3)
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "exports"

            result = export_godaddy_csv(products, output_dir, batch_size=2)

            file_names = [file.path.name for file in result.files]
            row_counts = [file.row_count for file in result.files]

        self.assertEqual(file_names, ["godaddy-import-001.csv", "godaddy-import-002.csv"])
        self.assertEqual(row_counts, [2, 1])
        self.assertEqual(result.products_exported, 3)

    def test_default_batch_size_splits_at_100_rows(self) -> None:
        products = [
            canonical_product(canonical_sku=f"UPC-{index}", source_sku=f"SRC-{index}")
            for index in range(101)
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            result = export_godaddy_csv(products, Path(temp_dir))

        self.assertEqual([file.row_count for file in result.files], [100, 1])
        self.assertEqual(result.products_exported, 101)

    def test_custom_filename_prefix_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "exports"

            result = export_godaddy_csv([canonical_product()], output_dir, filename_prefix="custom")

        self.assertEqual(result.files[0].path.name, "custom-001.csv")

    def test_rejects_invalid_batch_size(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                export_godaddy_csv([canonical_product()], Path(temp_dir), batch_size=0)

    def test_skips_product_without_selected_offer_and_writes_no_empty_file(self) -> None:
        source_offer = offer()
        product = CanonicalProduct(
            identity=source_offer.identity,
            details=source_offer.details,
            offers=(source_offer,),
            selected_offer=None,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "exports"

            result = export_godaddy_csv([product], output_dir)

            self.assertFalse(output_dir.exists())

        self.assertEqual(result.files, ())
        self.assertEqual(result.products_seen, 1)
        self.assertEqual(result.products_exported, 0)
        self.assertEqual(result.products_skipped, 1)
        self.assertTrue(any(message.code == "godaddy_missing_selected_offer" for message in result.messages))

    def test_skips_non_physical_product_type(self) -> None:
        product = canonical_product(product_type="DIGITAL")
        with tempfile.TemporaryDirectory() as temp_dir:
            result = export_godaddy_csv([product], Path(temp_dir))

        self.assertEqual(result.files, ())
        self.assertEqual(result.products_skipped, 1)
        self.assertTrue(any(message.field == "TYPE" for message in result.messages))
        self.assertTrue(any(message.code == "godaddy_invalid_field_value" for message in result.messages))

    def test_skips_unsupported_status(self) -> None:
        product = canonical_product(status="PENDING")
        with tempfile.TemporaryDirectory() as temp_dir:
            result = export_godaddy_csv([product], Path(temp_dir))

        self.assertEqual(result.files, ())
        self.assertEqual(result.products_skipped, 1)
        self.assertTrue(any(message.field == "STATUS" for message in result.messages))
        self.assertTrue(any(message.code == "godaddy_invalid_field_value" for message in result.messages))

    def test_type_and_status_are_written_uppercase(self) -> None:
        product = canonical_product(product_type="physical", status="draft")
        with tempfile.TemporaryDirectory() as temp_dir:
            result = export_godaddy_csv([product], Path(temp_dir))
            rows = self._read_csv(result.files[0].path)

        self.assertEqual(rows.rows[0]["TYPE"], "PHYSICAL")
        self.assertEqual(rows.rows[0]["STATUS"], "DRAFT")

    def test_update_mode_fails_safely_even_with_lookup_hook(self) -> None:
        class Lookup:
            def find_product_id(self, product: CanonicalProduct) -> str | None:
                return "godaddy-id"

        configuration = RunConfiguration(export_mode=ExportMode.UPDATE)
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "exports"

            result = export_godaddy_csv(
                [canonical_product()],
                output_dir,
                configuration,
                product_id_lookup=Lookup(),
            )

            self.assertFalse(output_dir.exists())

        self.assertEqual(result.files, ())
        self.assertEqual(result.products_seen, 1)
        self.assertEqual(result.products_exported, 0)
        self.assertEqual(result.products_skipped, 1)
        self.assertTrue(any(message.code == "godaddy_update_mode_not_supported" for message in result.messages))

    def test_compliance_notes_are_appended_without_duplicates(self) -> None:
        product = canonical_product(
            description="Sample Description\n\nFFL required.",
            compliance=ComplianceFlags(ffl_required=True, sot_required=True, nfa_item=True),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            result = export_godaddy_csv([product], Path(temp_dir))
            rows = self._read_csv(result.files[0].path)

        description = rows.rows[0]["DESCRIPTION"]
        self.assertEqual(description.count("FFL required."), 1)
        self.assertIn("SOT required.", description)
        self.assertIn("NFA item.", description)

    def test_image_policy_can_blank_image_url(self) -> None:
        configuration = RunConfiguration(images=ImagePolicy(include_image_urls=False))
        with tempfile.TemporaryDirectory() as temp_dir:
            result = export_godaddy_csv([canonical_product()], Path(temp_dir), configuration)
            rows = self._read_csv(result.files[0].path)

        self.assertEqual(rows.rows[0]["IMAGE URL"], "")

    def _read_csv(self, path: Path) -> CsvRows:
        with path.open(newline="", encoding="utf-8") as input_file:
            reader = csv.DictReader(input_file)
            return CsvRows(fieldnames=reader.fieldnames or [], rows=list(reader))


class CsvRows:
    def __init__(self, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        self.fieldnames = fieldnames
        self.rows = rows


def canonical_product(
    *,
    canonical_sku: str = "UPC-736676037018",
    source_sku: str = "SRC-1",
    description: str = "Sample Description",
    compliance: ComplianceFlags | None = None,
    product_type: str = "PHYSICAL",
    status: str = "ACTIVE",
) -> CanonicalProduct:
    source_offer = offer(
        canonical_sku=canonical_sku,
        source_sku=source_sku,
        description=description,
        compliance=compliance or ComplianceFlags(),
        product_type=product_type,
        status=status,
    )
    return CanonicalProduct(
        identity=source_offer.identity,
        details=source_offer.details,
        offers=(source_offer,),
        selected_offer=source_offer,
    )


def offer(
    *,
    canonical_sku: str = "UPC-736676037018",
    source_sku: str = "SRC-1",
    description: str = "Sample Description",
    compliance: ComplianceFlags | None = None,
    product_type: str = "PHYSICAL",
    status: str = "ACTIVE",
) -> SourceOffer:
    return SourceOffer(
        source=SourceInfo(distributor="sample", source_sku=source_sku),
        identity=ProductIdentity(
            canonical_sku=canonical_sku,
            upc="736676037018",
            manufacturer="Sample Maker",
            brand="Sample Brand",
            model_number="MODEL-1",
        ),
        details=ProductDetails(
            name="Sample Product",
            description=description,
            product_type=product_type,
            status=status,
        ),
        pricing=ProductPricing(
            unit_cost=Decimal("400.00"),
            calculated_price=Decimal("525.00"),
            msrp=Decimal("600.00"),
            sale_price=Decimal("500.50"),
        ),
        inventory=InventoryAvailability(
            status=AvailabilityStatus.AVAILABLE,
            quantity=3,
            track_inventory=True,
            allow_backorder=False,
            is_exportable_by_default=True,
        ),
        shipping=ShippingDetails(
            weight=Decimal("3.25"),
            length=Decimal("12.00"),
            width=Decimal("8.50"),
            height=Decimal("4.00"),
            free_shipping=True,
            fixed_shipping_fee=Decimal("12.30"),
        ),
        compliance=compliance or ComplianceFlags(),
        media=ProductMedia(
            image_url="https://example.com/product.jpg",
            image_name="product.jpg",
            image_source="sample",
        ),
    )


if __name__ == "__main__":
    unittest.main()
