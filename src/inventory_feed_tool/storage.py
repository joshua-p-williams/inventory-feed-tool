from __future__ import annotations

import json
import os
import platform
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from inventory_feed_tool.models import (
    AvailabilityPolicy,
    ComplianceBehavior,
    CompliancePolicy,
    ExportMode,
    ImagePolicy,
    MapMode,
    MissingImageBehavior,
    PricingProfile,
    RoundingMode,
    RunConfiguration,
    SalePriceMode,
    SourceOffer,
    SourceSelectionPolicy,
    SourceSelectionStrategy,
)


SCHEMA_VERSION = 1
DEFAULT_TARGET_SYSTEM = "godaddy"
RUN_CONFIGURATION_SETTING_KEY = "run_configuration.default"


@dataclass(frozen=True)
class ExternalProductMapping:
    id: int
    target_system: str
    canonical_sku: str
    upc: str | None = None
    distributor: str | None = None
    source_sku: str | None = None
    external_product_id: str | None = None
    last_seen_export_run_id: int | None = None
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class SourceOverride:
    id: int
    target_system: str
    canonical_sku: str
    upc: str | None = None
    preferred_distributor: str | None = None
    preferred_source_sku: str | None = None
    created_at: str = ""
    updated_at: str = ""


def default_database_path() -> Path:
    system = platform.system()

    if system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return base / "InventoryFeedTool" / "inventory-feed-tool.sqlite3"

    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "InventoryFeedTool" / "inventory-feed-tool.sqlite3"

    base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "inventory-feed-tool" / "inventory-feed-tool.sqlite3"


def connect_database(path: Path | None = None) -> sqlite3.Connection:
    database_path = path or default_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    version = _schema_version(connection)

    if version > SCHEMA_VERSION:
        raise RuntimeError(
            f"Database schema version {version} is newer than supported version {SCHEMA_VERSION}."
        )

    if version < 1:
        _apply_schema_v1(connection)
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        connection.commit()


class LocalStore:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    @classmethod
    def open(cls, path: Path | None = None) -> "LocalStore":
        connection = connect_database(path)
        initialize_database(connection)
        return cls(connection)

    def close(self) -> None:
        self.connection.close()

    def save_setting(self, key: str, value: str) -> None:
        now = _utc_now()
        self.connection.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
              value = excluded.value,
              updated_at = excluded.updated_at
            """,
            (key, value, now),
        )
        self.connection.commit()

    def load_setting(self, key: str) -> str | None:
        row = self.connection.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            (key,),
        ).fetchone()
        return row["value"] if row else None

    def save_run_configuration(self, configuration: RunConfiguration) -> None:
        self.save_setting(RUN_CONFIGURATION_SETTING_KEY, run_configuration_to_json(configuration))

    def load_run_configuration(self) -> RunConfiguration:
        value = self.load_setting(RUN_CONFIGURATION_SETTING_KEY)
        if value is None:
            return RunConfiguration()
        return run_configuration_from_json(value)

    def create_export_run(
        self,
        configuration: RunConfiguration,
        *,
        output_folder: str | None = None,
        notes: str | None = None,
    ) -> int:
        cursor = self.connection.execute(
            """
            INSERT INTO export_runs (created_at, export_mode, output_folder, configuration_json, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                _utc_now(),
                configuration.export_mode.value,
                output_folder,
                run_configuration_to_json(configuration),
                notes,
            ),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def upsert_external_product_mapping(
        self,
        *,
        target_system: str,
        canonical_sku: str,
        upc: str | None = None,
        distributor: str | None = None,
        source_sku: str | None = None,
        external_product_id: str | None = None,
        last_seen_export_run_id: int | None = None,
    ) -> ExternalProductMapping:
        _require_text(target_system, "target_system")
        _require_text(canonical_sku, "canonical_sku")
        now = _utc_now()
        self.connection.execute(
            """
            INSERT INTO external_product_mappings (
              target_system,
              canonical_sku,
              upc,
              distributor,
              source_sku,
              external_product_id,
              last_seen_export_run_id,
              created_at,
              updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(target_system, canonical_sku) DO UPDATE SET
              upc = excluded.upc,
              distributor = excluded.distributor,
              source_sku = excluded.source_sku,
              external_product_id = excluded.external_product_id,
              last_seen_export_run_id = excluded.last_seen_export_run_id,
              updated_at = excluded.updated_at
            """,
            (
                target_system,
                canonical_sku,
                upc,
                distributor,
                source_sku,
                external_product_id,
                last_seen_export_run_id,
                now,
                now,
            ),
        )
        self.connection.commit()
        mapping = self.find_external_product_mapping(target_system=target_system, canonical_sku=canonical_sku)
        if mapping is None:
            raise RuntimeError("external product mapping upsert failed")
        return mapping

    def find_external_product_mapping(
        self,
        *,
        target_system: str,
        canonical_sku: str | None = None,
        upc: str | None = None,
    ) -> ExternalProductMapping | None:
        _require_text(target_system, "target_system")
        if canonical_sku is None and upc is None:
            raise ValueError("canonical_sku or upc is required")

        row = None
        if canonical_sku is not None:
            row = self.connection.execute(
                """
                SELECT * FROM external_product_mappings
                WHERE target_system = ? AND canonical_sku = ?
                """,
                (target_system, canonical_sku),
            ).fetchone()

        if row is None and upc is not None:
            row = self.connection.execute(
                """
                SELECT * FROM external_product_mappings
                WHERE target_system = ? AND upc = ?
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """,
                (target_system, upc),
            ).fetchone()

        return _external_product_mapping_from_row(row) if row else None

    def record_source_offer_snapshot(
        self,
        export_run_id: int,
        offer: SourceOffer,
        *,
        is_selected: bool = False,
        payload: dict[str, Any] | None = None,
    ) -> int:
        snapshot_payload = payload if payload is not None else source_offer_payload(offer)
        cursor = self.connection.execute(
            """
            INSERT INTO source_offers (
              export_run_id,
              canonical_sku,
              upc,
              distributor,
              source_sku,
              unit_cost,
              calculated_price,
              quantity,
              raw_quantity,
              availability_status,
              map_price,
              is_selected,
              payload_json,
              created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                export_run_id,
                offer.identity.canonical_sku,
                offer.identity.upc,
                offer.source.distributor,
                offer.source.source_sku,
                _decimal_to_text(offer.pricing.unit_cost),
                _decimal_to_text(offer.pricing.calculated_price),
                offer.inventory.quantity,
                offer.inventory.raw_quantity,
                offer.inventory.status.value,
                _decimal_to_text(offer.pricing.map_price),
                1 if is_selected else 0,
                json.dumps(snapshot_payload, sort_keys=True),
                _utc_now(),
            ),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def upsert_source_override(
        self,
        *,
        target_system: str,
        canonical_sku: str,
        upc: str | None = None,
        preferred_distributor: str | None = None,
        preferred_source_sku: str | None = None,
    ) -> SourceOverride:
        _require_text(target_system, "target_system")
        _require_text(canonical_sku, "canonical_sku")
        now = _utc_now()
        self.connection.execute(
            """
            INSERT INTO source_overrides (
              target_system,
              canonical_sku,
              upc,
              preferred_distributor,
              preferred_source_sku,
              created_at,
              updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(target_system, canonical_sku) DO UPDATE SET
              upc = excluded.upc,
              preferred_distributor = excluded.preferred_distributor,
              preferred_source_sku = excluded.preferred_source_sku,
              updated_at = excluded.updated_at
            """,
            (
                target_system,
                canonical_sku,
                upc,
                preferred_distributor,
                preferred_source_sku,
                now,
                now,
            ),
        )
        self.connection.commit()
        override = self.find_source_override(target_system=target_system, canonical_sku=canonical_sku)
        if override is None:
            raise RuntimeError("source override upsert failed")
        return override

    def find_source_override(
        self,
        *,
        target_system: str,
        canonical_sku: str | None = None,
        upc: str | None = None,
    ) -> SourceOverride | None:
        _require_text(target_system, "target_system")
        if canonical_sku is None and upc is None:
            raise ValueError("canonical_sku or upc is required")

        row = None
        if canonical_sku is not None:
            row = self.connection.execute(
                """
                SELECT * FROM source_overrides
                WHERE target_system = ? AND canonical_sku = ?
                """,
                (target_system, canonical_sku),
            ).fetchone()

        if row is None and upc is not None:
            row = self.connection.execute(
                """
                SELECT * FROM source_overrides
                WHERE target_system = ? AND upc = ?
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """,
                (target_system, upc),
            ).fetchone()

        return _source_override_from_row(row) if row else None


def run_configuration_to_dict(configuration: RunConfiguration) -> dict[str, Any]:
    return {
        "export_mode": configuration.export_mode.value,
        "pricing": {
            "markup_percent": str(configuration.pricing.markup_percent),
            "map_mode": configuration.pricing.map_mode.value,
            "sale_price_mode": configuration.pricing.sale_price_mode.value,
            "rounding_mode": configuration.pricing.rounding_mode.value,
        },
        "availability": {
            "include_zero_quantity": configuration.availability.include_zero_quantity,
            "include_allocated": configuration.availability.include_allocated,
            "include_unknown_quantity": configuration.availability.include_unknown_quantity,
            "approximate_quantity_floor": configuration.availability.approximate_quantity_floor,
            "allow_backorder": configuration.availability.allow_backorder,
        },
        "source_selection": {
            "strategy": configuration.source_selection.strategy.value,
            "preferred_distributors": list(configuration.source_selection.preferred_distributors),
            "allow_manual_overrides": configuration.source_selection.allow_manual_overrides,
        },
        "images": {
            "include_image_urls": configuration.images.include_image_urls,
            "missing_image_behavior": configuration.images.missing_image_behavior.value,
            "validate_image_urls": configuration.images.validate_image_urls,
        },
        "compliance": {
            "ffl_required_behavior": configuration.compliance.ffl_required_behavior.value,
            "sot_required_behavior": configuration.compliance.sot_required_behavior.value,
            "nfa_item_behavior": configuration.compliance.nfa_item_behavior.value,
        },
    }


def run_configuration_to_json(configuration: RunConfiguration) -> str:
    return json.dumps(run_configuration_to_dict(configuration), sort_keys=True)


def run_configuration_from_json(value: str) -> RunConfiguration:
    raw = json.loads(value)
    if not isinstance(raw, dict):
        raise ValueError("Run configuration JSON must be an object")
    return run_configuration_from_dict(raw)


def run_configuration_from_dict(raw: dict[str, Any]) -> RunConfiguration:
    default = RunConfiguration()
    pricing = _dict_value(raw, "pricing")
    availability = _dict_value(raw, "availability")
    source_selection = _dict_value(raw, "source_selection")
    images = _dict_value(raw, "images")
    compliance = _dict_value(raw, "compliance")

    return RunConfiguration(
        export_mode=_enum_value(ExportMode, raw.get("export_mode"), default.export_mode),
        pricing=PricingProfile(
            markup_percent=Decimal(str(pricing.get("markup_percent", default.pricing.markup_percent))),
            map_mode=_enum_value(MapMode, pricing.get("map_mode"), default.pricing.map_mode),
            sale_price_mode=_enum_value(
                SalePriceMode,
                pricing.get("sale_price_mode"),
                default.pricing.sale_price_mode,
            ),
            rounding_mode=_enum_value(
                RoundingMode,
                pricing.get("rounding_mode"),
                default.pricing.rounding_mode,
            ),
        ),
        availability=AvailabilityPolicy(
            include_zero_quantity=_bool_value(
                availability.get("include_zero_quantity"),
                default.availability.include_zero_quantity,
            ),
            include_allocated=_bool_value(
                availability.get("include_allocated"),
                default.availability.include_allocated,
            ),
            include_unknown_quantity=_bool_value(
                availability.get("include_unknown_quantity"),
                default.availability.include_unknown_quantity,
            ),
            approximate_quantity_floor=int(
                availability.get(
                    "approximate_quantity_floor",
                    default.availability.approximate_quantity_floor,
                )
            ),
            allow_backorder=_bool_value(availability.get("allow_backorder"), default.availability.allow_backorder),
        ),
        source_selection=SourceSelectionPolicy(
            strategy=_enum_value(
                SourceSelectionStrategy,
                source_selection.get("strategy"),
                default.source_selection.strategy,
            ),
            preferred_distributors=tuple(source_selection.get("preferred_distributors", ())),
            allow_manual_overrides=_bool_value(
                source_selection.get("allow_manual_overrides"),
                default.source_selection.allow_manual_overrides,
            ),
        ),
        images=ImagePolicy(
            include_image_urls=_bool_value(images.get("include_image_urls"), default.images.include_image_urls),
            missing_image_behavior=_enum_value(
                MissingImageBehavior,
                images.get("missing_image_behavior"),
                default.images.missing_image_behavior,
            ),
            validate_image_urls=_bool_value(images.get("validate_image_urls"), default.images.validate_image_urls),
        ),
        compliance=CompliancePolicy(
            ffl_required_behavior=_enum_value(
                ComplianceBehavior,
                compliance.get("ffl_required_behavior"),
                default.compliance.ffl_required_behavior,
            ),
            sot_required_behavior=_enum_value(
                ComplianceBehavior,
                compliance.get("sot_required_behavior"),
                default.compliance.sot_required_behavior,
            ),
            nfa_item_behavior=_enum_value(
                ComplianceBehavior,
                compliance.get("nfa_item_behavior"),
                default.compliance.nfa_item_behavior,
            ),
        ),
    )


def source_offer_payload(offer: SourceOffer) -> dict[str, Any]:
    return {
        "source": {
            "distributor": offer.source.distributor,
            "source_sku": offer.source.source_sku,
            "source_file": offer.source.source_file,
            "source_row_number": offer.source.source_row_number,
            "raw_identifier": offer.source.raw_identifier,
        },
        "identity": {
            "canonical_sku": offer.identity.canonical_sku,
            "upc": offer.identity.upc,
            "manufacturer": offer.identity.manufacturer,
            "brand": offer.identity.brand,
            "model_number": offer.identity.model_number,
            "model_name": offer.identity.model_name,
        },
        "details": {
            "name": offer.details.name,
            "description": offer.details.description,
            "product_type": offer.details.product_type,
            "category": offer.details.category,
            "family": offer.details.family,
            "status": offer.details.status,
        },
        "pricing": {
            "unit_cost": _decimal_to_text(offer.pricing.unit_cost),
            "calculated_price": _decimal_to_text(offer.pricing.calculated_price),
            "msrp": _decimal_to_text(offer.pricing.msrp),
            "map_price": _decimal_to_text(offer.pricing.map_price),
            "retail_price": _decimal_to_text(offer.pricing.retail_price),
            "sale_price": _decimal_to_text(offer.pricing.sale_price),
            "pricing_reason": offer.pricing.pricing_reason,
        },
        "inventory": {
            "status": offer.inventory.status.value,
            "quantity": offer.inventory.quantity,
            "raw_quantity": offer.inventory.raw_quantity,
            "track_inventory": offer.inventory.track_inventory,
            "allow_backorder": offer.inventory.allow_backorder,
            "availability_note": offer.inventory.availability_note,
            "is_exportable_by_default": offer.inventory.is_exportable_by_default,
        },
        "shipping": {
            "weight": _decimal_to_text(offer.shipping.weight),
            "length": _decimal_to_text(offer.shipping.length),
            "width": _decimal_to_text(offer.shipping.width),
            "height": _decimal_to_text(offer.shipping.height),
            "disable_shipping": offer.shipping.disable_shipping,
            "free_shipping": offer.shipping.free_shipping,
            "fixed_shipping_fee": _decimal_to_text(offer.shipping.fixed_shipping_fee),
        },
        "compliance": {
            "ffl_required": offer.compliance.ffl_required,
            "sot_required": offer.compliance.sot_required,
            "nfa_item": offer.compliance.nfa_item,
            "country_of_origin": offer.compliance.country_of_origin,
        },
        "media": {
            "image_url": offer.media.image_url,
            "image_name": offer.media.image_name,
            "image_source": offer.media.image_source,
        },
        "attributes": offer.attributes,
    }


def _apply_schema_v1(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS export_runs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          created_at TEXT NOT NULL,
          export_mode TEXT NOT NULL,
          output_folder TEXT,
          configuration_json TEXT NOT NULL,
          notes TEXT
        );

        CREATE TABLE IF NOT EXISTS external_product_mappings (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          target_system TEXT NOT NULL,
          canonical_sku TEXT NOT NULL,
          upc TEXT,
          distributor TEXT,
          source_sku TEXT,
          external_product_id TEXT,
          last_seen_export_run_id INTEGER,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          UNIQUE(target_system, canonical_sku),
          FOREIGN KEY(last_seen_export_run_id) REFERENCES export_runs(id)
        );

        CREATE INDEX IF NOT EXISTS idx_external_product_mappings_target_upc
          ON external_product_mappings(target_system, upc);

        CREATE TABLE IF NOT EXISTS source_offers (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          export_run_id INTEGER NOT NULL,
          canonical_sku TEXT NOT NULL,
          upc TEXT,
          distributor TEXT NOT NULL,
          source_sku TEXT NOT NULL,
          unit_cost TEXT,
          calculated_price TEXT,
          quantity INTEGER,
          raw_quantity TEXT,
          availability_status TEXT,
          map_price TEXT,
          is_selected INTEGER NOT NULL DEFAULT 0,
          payload_json TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(export_run_id) REFERENCES export_runs(id)
        );

        CREATE INDEX IF NOT EXISTS idx_source_offers_export_run_id
          ON source_offers(export_run_id);

        CREATE INDEX IF NOT EXISTS idx_source_offers_canonical_sku
          ON source_offers(canonical_sku);

        CREATE TABLE IF NOT EXISTS source_overrides (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          target_system TEXT NOT NULL,
          canonical_sku TEXT NOT NULL,
          upc TEXT,
          preferred_distributor TEXT,
          preferred_source_sku TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          UNIQUE(target_system, canonical_sku)
        );

        CREATE INDEX IF NOT EXISTS idx_source_overrides_target_upc
          ON source_overrides(target_system, upc);
        """
    )


def _schema_version(connection: sqlite3.Connection) -> int:
    row = connection.execute("PRAGMA user_version").fetchone()
    return int(row[0])


def _dict_value(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key, {})
    return value if isinstance(value, dict) else {}


def _enum_value(enum_type: type[Enum], value: object, default: Any) -> Any:
    if value is None:
        return default
    try:
        return enum_type(str(value))
    except ValueError:
        return default


def _bool_value(value: object, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "t", "yes", "y"}:
            return True
        if normalized in {"0", "false", "f", "no", "n"}:
            return False
    return default


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _decimal_to_text(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _external_product_mapping_from_row(row: sqlite3.Row) -> ExternalProductMapping:
    return ExternalProductMapping(
        id=int(row["id"]),
        target_system=row["target_system"],
        canonical_sku=row["canonical_sku"],
        upc=row["upc"],
        distributor=row["distributor"],
        source_sku=row["source_sku"],
        external_product_id=row["external_product_id"],
        last_seen_export_run_id=row["last_seen_export_run_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _source_override_from_row(row: sqlite3.Row) -> SourceOverride:
    return SourceOverride(
        id=int(row["id"]),
        target_system=row["target_system"],
        canonical_sku=row["canonical_sku"],
        upc=row["upc"],
        preferred_distributor=row["preferred_distributor"],
        preferred_source_sku=row["preferred_source_sku"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
