from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum

from inventory_feed_tool.validation import ConflictMessage, ValidationMessage


class ExportMode(StrEnum):
    NEW = "new"
    UPDATE = "update"


class MapMode(StrEnum):
    RESPECT = "respect"
    IGNORE = "ignore"


class SalePriceMode(StrEnum):
    IGNORE = "ignore"
    USE_SOURCE_SALE = "use_source_sale"
    FUTURE_MANUAL = "future_manual"


class RoundingMode(StrEnum):
    NEAREST_CENT = "nearest_cent"
    NEAREST_DOLLAR = "nearest_dollar"
    CHARM_99 = "charm_99"


class AvailabilityStatus(StrEnum):
    AVAILABLE = "available"
    OUT_OF_STOCK = "out_of_stock"
    ALLOCATED = "allocated"
    UNKNOWN = "unknown"
    DISCONTINUED = "discontinued"


class SourceSelectionStrategy(StrEnum):
    GROSS_PROFIT = "gross_profit"
    QUANTITY = "quantity"
    DISTRIBUTOR_PRIORITY = "distributor_priority"


class MissingImageBehavior(StrEnum):
    WARN = "warn"
    BLANK = "blank"
    BLOCK_ROW = "block_row"


class ComplianceBehavior(StrEnum):
    DESCRIPTION_NOTE = "description_note"
    EXCLUDE = "exclude"
    IGNORE = "ignore"


@dataclass(frozen=True)
class PricingProfile:
    markup_percent: Decimal = Decimal("25")
    map_mode: MapMode = MapMode.RESPECT
    sale_price_mode: SalePriceMode = SalePriceMode.IGNORE
    rounding_mode: RoundingMode = RoundingMode.NEAREST_CENT

    def __post_init__(self) -> None:
        if self.markup_percent < 0:
            raise ValueError("markup_percent cannot be negative")


@dataclass(frozen=True)
class AvailabilityPolicy:
    include_zero_quantity: bool = False
    include_allocated: bool = False
    include_unknown_quantity: bool = False
    approximate_quantity_floor: int = 0
    allow_backorder: bool = False

    def __post_init__(self) -> None:
        if self.approximate_quantity_floor < 0:
            raise ValueError("approximate_quantity_floor cannot be negative")


@dataclass(frozen=True)
class SourceSelectionPolicy:
    strategy: SourceSelectionStrategy = SourceSelectionStrategy.GROSS_PROFIT
    preferred_distributors: tuple[str, ...] = ()
    allow_manual_overrides: bool = True


@dataclass(frozen=True)
class ImagePolicy:
    include_image_urls: bool = True
    missing_image_behavior: MissingImageBehavior = MissingImageBehavior.WARN
    validate_image_urls: bool = False


@dataclass(frozen=True)
class CompliancePolicy:
    ffl_required_behavior: ComplianceBehavior = ComplianceBehavior.DESCRIPTION_NOTE
    sot_required_behavior: ComplianceBehavior = ComplianceBehavior.DESCRIPTION_NOTE
    nfa_item_behavior: ComplianceBehavior = ComplianceBehavior.DESCRIPTION_NOTE


@dataclass(frozen=True)
class RunConfiguration:
    export_mode: ExportMode = ExportMode.NEW
    pricing: PricingProfile = field(default_factory=PricingProfile)
    availability: AvailabilityPolicy = field(default_factory=AvailabilityPolicy)
    source_selection: SourceSelectionPolicy = field(default_factory=SourceSelectionPolicy)
    images: ImagePolicy = field(default_factory=ImagePolicy)
    compliance: CompliancePolicy = field(default_factory=CompliancePolicy)


@dataclass(frozen=True)
class SourceInfo:
    distributor: str
    source_sku: str
    source_file: str | None = None
    source_row_number: int | None = None
    raw_identifier: str | None = None

    def __post_init__(self) -> None:
        if not self.distributor.strip():
            raise ValueError("distributor is required")
        if not self.source_sku.strip():
            raise ValueError("source_sku is required")

    @property
    def display_name(self) -> str:
        return f"{self.distributor}:{self.source_sku}"


@dataclass(frozen=True)
class ProductIdentity:
    canonical_sku: str
    upc: str | None = None
    ean: str | None = None
    gtin: str | None = None
    isbn: str | None = None
    manufacturer: str | None = None
    brand: str | None = None
    model_number: str | None = None
    model_name: str | None = None

    def __post_init__(self) -> None:
        if not self.canonical_sku.strip():
            raise ValueError("canonical_sku is required")


@dataclass(frozen=True)
class ProductDetails:
    name: str
    description: str = ""
    product_type: str = "PHYSICAL"
    category: str | None = None
    family: str | None = None
    status: str = "ACTIVE"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name is required")


@dataclass(frozen=True)
class ProductPricing:
    unit_cost: Decimal
    calculated_price: Decimal
    msrp: Decimal | None = None
    map_price: Decimal | None = None
    retail_price: Decimal | None = None
    sale_price: Decimal | None = None
    sale_ends: date | None = None
    pricing_reason: str = ""

    def __post_init__(self) -> None:
        if self.unit_cost < 0:
            raise ValueError("unit_cost cannot be negative")
        if self.calculated_price < 0:
            raise ValueError("calculated_price cannot be negative")


@dataclass(frozen=True)
class InventoryAvailability:
    status: AvailabilityStatus
    quantity: int
    raw_quantity: str | None = None
    track_inventory: bool = True
    allow_backorder: bool = False
    availability_note: str = ""
    is_exportable_by_default: bool = True

    def __post_init__(self) -> None:
        if self.quantity < 0:
            raise ValueError("quantity cannot be negative")


@dataclass(frozen=True)
class ShippingDetails:
    weight: Decimal | None = None
    length: Decimal | None = None
    width: Decimal | None = None
    height: Decimal | None = None
    disable_shipping: bool = False
    free_shipping: bool = False
    fixed_shipping_fee: Decimal | None = None


@dataclass(frozen=True)
class ComplianceFlags:
    ffl_required: bool = False
    sot_required: bool = False
    nfa_item: bool = False
    country_of_origin: str | None = None

    def description_notes(self, policy: CompliancePolicy | None = None) -> tuple[str, ...]:
        policy = policy or CompliancePolicy()
        notes: list[str] = []

        if self.ffl_required and policy.ffl_required_behavior == ComplianceBehavior.DESCRIPTION_NOTE:
            notes.append("FFL required.")
        if self.sot_required and policy.sot_required_behavior == ComplianceBehavior.DESCRIPTION_NOTE:
            notes.append("SOT required.")
        if self.nfa_item and policy.nfa_item_behavior == ComplianceBehavior.DESCRIPTION_NOTE:
            notes.append("NFA item.")

        return tuple(notes)


@dataclass(frozen=True)
class ProductMedia:
    image_url: str | None = None
    image_name: str | None = None
    image_source: str | None = None


@dataclass(frozen=True)
class SourceOffer:
    source: SourceInfo
    identity: ProductIdentity
    details: ProductDetails
    pricing: ProductPricing
    inventory: InventoryAvailability
    shipping: ShippingDetails = field(default_factory=ShippingDetails)
    compliance: ComplianceFlags = field(default_factory=ComplianceFlags)
    media: ProductMedia = field(default_factory=ProductMedia)
    attributes: dict[str, str] = field(default_factory=dict)
    warnings: tuple[ValidationMessage, ...] = ()


@dataclass(frozen=True)
class CanonicalProduct:
    identity: ProductIdentity
    details: ProductDetails
    offers: tuple[SourceOffer, ...]
    selected_offer: SourceOffer | None = None
    conflicts: tuple[ConflictMessage, ...] = ()
    warnings: tuple[ValidationMessage, ...] = ()

    def __post_init__(self) -> None:
        if not self.offers:
            raise ValueError("offers must contain at least one SourceOffer")
        if self.selected_offer is not None and self.selected_offer not in self.offers:
            raise ValueError("selected_offer must be included in offers")


def canonical_sku_from_upc(upc: str) -> str:
    normalized = "".join(character for character in upc if character.isdigit())
    if not normalized:
        raise ValueError("upc must contain at least one digit")
    return f"UPC-{normalized}"


def fallback_canonical_sku(distributor: str, source_sku: str) -> str:
    distributor_code = distributor.strip().upper()[:3]
    source_code = source_sku.strip().upper()
    if not distributor_code or not source_code:
        raise ValueError("distributor and source_sku are required")
    return f"{distributor_code}-{source_code}"
