"""
Quotation Schema v1 (FROZEN)

This module is the single source of truth for the quotation record shape
agreed in the schema design. It intentionally has no external dependencies
(no pydantic, no ORM) so it can be dropped into any pipeline and adapted.

Design principles encoded here, not just documented:
  - "unknown" / "unresolved" are first-class values, never silently defaulted.
  - Only `SourceType.GENUINE_QUOTATION` (or clearly labeled synthetic) records
    may feed a real quotation-comparison result — enforced in code, not by
    convention. See `assert_usable_for_comparison`.
  - Monetary values always carry their currency; identifiers always carry
    their scheme.
  - Currency conversion is optional, additive, and never overwrites the
    original stated total.
  - Category mapping confidence of "approximate" must surface a warning,
    not just a label someone can ignore.

Next step (not done here): map real_intake.py / real_procurement.py fields
onto this structure. This file defines the target shape and the invariants
that mapping step must satisfy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SourceType(str, Enum):
    GENUINE_QUOTATION = "genuine_quotation"
    AWARD_NOTICE = "award_notice"
    PRICE_REGISTRATION = "price_registration"  # e.g. Brazil ARP
    CATALOG_ENTRY = "catalog_entry"
    SYNTHETIC = "synthetic"


class RealOrSynthetic(str, Enum):
    REAL = "real"
    SYNTHETIC = "synthetic"


class IdentifierScheme(str, Enum):
    RUT = "RUT"
    CNPJ = "CNPJ"
    EDRPOU = "EDRPOU"
    UEI = "UEI"
    OCDS_PARTY_ID = "OCDS-party-id"
    NONE = "none"


class EntityLinkStatus(str, Enum):
    UNLINKED = "unlinked"
    LINKED_BY_ID_MATCH = "linked_by_id_match"
    LINKED_BY_MANUAL_REVIEW = "linked_by_manual_review"


class CategoryMappingConfidence(str, Enum):
    EXACT = "exact"
    APPROXIMATE = "approximate"
    UNMAPPED = "unmapped"


class TaxStatus(str, Enum):
    INCLUDED = "included"
    EXCLUDED = "excluded"
    UNKNOWN = "unknown"


class CommitmentType(str, Enum):
    FIXED_DATE = "fixed_date"
    LEAD_TIME_DAYS = "lead_time_days"
    UNSPECIFIED = "unspecified"


class ValidityStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"
    SUPERSEDED = "superseded"
    NO_EXPIRY_STATED = "no_expiry_stated"


class Materiality(str, Enum):
    MINOR = "minor"
    SIGNIFICANT = "significant"


# ---------------------------------------------------------------------------
# Section 1: Provenance
# ---------------------------------------------------------------------------

@dataclass
class Provenance:
    record_id: str
    source_document: str
    source_type: SourceType
    source_organization: str
    retrieved_at: datetime
    real_or_synthetic: RealOrSynthetic

    def __post_init__(self) -> None:
        # Deliberate redundancy: source_type and real_or_synthetic must agree.
        if self.source_type == SourceType.SYNTHETIC and self.real_or_synthetic != RealOrSynthetic.SYNTHETIC:
            raise ValueError(
                f"{self.record_id}: source_type=synthetic requires real_or_synthetic=synthetic"
            )
        if self.source_type != SourceType.SYNTHETIC and self.real_or_synthetic == RealOrSynthetic.SYNTHETIC:
            raise ValueError(
                f"{self.record_id}: real_or_synthetic=synthetic requires source_type=synthetic"
            )


# ---------------------------------------------------------------------------
# Section 2: Supplier
# ---------------------------------------------------------------------------

@dataclass
class Supplier:
    name_raw: str
    country: str  # ISO 3166-1 alpha-2
    id_scheme: IdentifierScheme
    id: Optional[str] = None
    entity_link_status: EntityLinkStatus = EntityLinkStatus.UNLINKED

    def __post_init__(self) -> None:
        if len(self.country) != 2 or not self.country.isalpha():
            raise ValueError(f"supplier_country must be ISO 3166-1 alpha-2, got {self.country!r}")
        if self.id_scheme != IdentifierScheme.NONE and not self.id:
            raise ValueError("supplier_id is required when supplier_id_scheme is not 'none'")
        # Linking must always be evidenced — never defaulted to linked.
        if self.entity_link_status != EntityLinkStatus.UNLINKED and not self.id:
            raise ValueError(
                "entity_link_status cannot be set to a linked state without a supplier_id as evidence"
            )


# ---------------------------------------------------------------------------
# Section 3: Product
# ---------------------------------------------------------------------------

@dataclass
class ClassificationCode:
    scheme: str  # e.g. "CATMAT", "CPV", "UNSPSC"
    code: str


@dataclass
class Specification:
    attribute: str
    value: str
    unit: Optional[str] = None


@dataclass
class Product:
    description_raw: str
    quantity: float
    unit_of_measure: str
    unit_scheme: str  # e.g. "UN/CEFACT", "source-native"
    internal_category: str
    category_mapping_confidence: CategoryMappingConfidence
    description_translated: Optional[str] = None
    specifications: List[Specification] = field(default_factory=list)
    source_classification: List[ClassificationCode] = field(default_factory=list)

    def requires_review_warning(self) -> bool:
        # Rule: approximate mapping must trigger a visible review warning.
        return self.category_mapping_confidence == CategoryMappingConfidence.APPROXIMATE

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if (
            self.category_mapping_confidence == CategoryMappingConfidence.UNMAPPED
            and self.internal_category
        ):
            raise ValueError(
                "internal_category should not be set when category_mapping_confidence is 'unmapped'"
            )


# ---------------------------------------------------------------------------
# Section 4: Costs
# ---------------------------------------------------------------------------

@dataclass
class OtherCharge:
    label: str
    amount: float


@dataclass
class Conversion:
    target_currency: str
    rate: float
    rate_date: date
    rate_source: str
    converted_amount: float

    def __post_init__(self) -> None:
        # All four provenance fields are mandatory together — no partial conversions.
        missing = [
            f for f, v in [
                ("target_currency", self.target_currency),
                ("rate", self.rate),
                ("rate_date", self.rate_date),
                ("rate_source", self.rate_source),
            ] if not v
        ]
        if missing:
            raise ValueError(f"Conversion missing required provenance fields: {missing}")


@dataclass
class Costs:
    currency: str  # ISO 4217
    goods_amount: float
    tax_status: TaxStatus
    total_payable_amount: float
    total_payable_is_computed: bool
    tax_amount: Optional[float] = None
    freight_amount: Optional[float] = None
    other_charges: List[OtherCharge] = field(default_factory=list)
    excluded_charges: List[str] = field(default_factory=list)
    conversion: Optional[Conversion] = None

    def ranking_amount(self, target_currency: Optional[str] = None) -> float:
        """
        Returns the value to use for cost ranking.
        - Same currency as target (or no target given): use the stated total directly.
        - Different currency: only use conversion.converted_amount, and callers
          MUST label it as an estimate — this method does not do UI labeling,
          it only enforces that a cross-currency comparison cannot silently
          use an unconverted number.
        """
        if target_currency is None or target_currency == self.currency:
            return self.total_payable_amount
        if self.conversion is None or self.conversion.target_currency != target_currency:
            raise ValueError(
                f"Cannot rank {self.currency} amount against {target_currency} "
                f"without a recorded conversion"
            )
        return self.conversion.converted_amount

    def __post_init__(self) -> None:
        self.tax_status = TaxStatus(self.tax_status)
        if self.tax_status == TaxStatus.EXCLUDED and not self.excluded_charges:
            # Not a hard error, but this is exactly the "unresolved, not silently
            # defaulted" case — the caller is responsible for surfacing it.
            pass
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValueError(f"currency must be ISO 4217, got {self.currency!r}")


# ---------------------------------------------------------------------------
# Section 5: Delivery
# ---------------------------------------------------------------------------

@dataclass
class DeliveryTermsStructured:
    """Optional structured extraction from delivery_conditions free text.
    Every field here is optional; original free text is always preserved
    separately on DeliveryTerms.conditions_raw."""
    late_delivery_penalty_stated: Optional[bool] = None
    late_delivery_penalty_text: Optional[str] = None
    partial_delivery_allowed: Optional[bool] = None
    incoterm: Optional[str] = None


@dataclass
class Delivery:
    delivery_country: str  # ISO 3166-1 alpha-2, distinct from supplier country
    delivery_destination: str
    commitment_type: CommitmentType
    commitment_date: Optional[date] = None
    lead_time_days: Optional[int] = None
    commitment_timezone: Optional[str] = None  # IANA tz name
    conditions_raw: Optional[str] = None
    conditions_structured: DeliveryTermsStructured = field(default_factory=DeliveryTermsStructured)

    def __post_init__(self) -> None:
        if self.commitment_type == CommitmentType.FIXED_DATE:
            if self.commitment_date is None or self.commitment_timezone is None:
                raise ValueError(
                    "commitment_type=fixed_date requires commitment_date and commitment_timezone"
                )
        elif self.commitment_type == CommitmentType.LEAD_TIME_DAYS:
            if self.lead_time_days is None or self.lead_time_days <= 0:
                raise ValueError(
                    "commitment_type=lead_time_days requires a positive lead_time_days"
                )
        # Structured fields must never exist without the raw text they were derived from,
        # unless nothing was stated at all.
        structured_populated = any(
            v is not None
            for v in (
                self.conditions_structured.late_delivery_penalty_stated,
                self.conditions_structured.late_delivery_penalty_text,
                self.conditions_structured.partial_delivery_allowed,
                self.conditions_structured.incoterm,
            )
        )
        if structured_populated and not self.conditions_raw:
            raise ValueError(
                "conditions_structured populated but conditions_raw is empty — "
                "original text must always be preserved"
            )


# ---------------------------------------------------------------------------
# Section 6: Validity
# ---------------------------------------------------------------------------

@dataclass
class Validity:
    issued_at: datetime
    status: ValidityStatus
    expires_at: Optional[datetime] = None
    revision_number: Optional[int] = None

    def __post_init__(self) -> None:
        if self.issued_at.tzinfo is None:
            raise ValueError("issued_at must be timezone-aware")
        if self.expires_at is not None and self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")
        if self.expires_at is None and self.status not in (
            ValidityStatus.NO_EXPIRY_STATED,
            ValidityStatus.WITHDRAWN,
            ValidityStatus.SUPERSEDED,
        ):
            raise ValueError(
                "expires_at is missing but status does not reflect that "
                "(expected no_expiry_stated/withdrawn/superseded)"
            )

    def compute_status(self, as_of: datetime) -> ValidityStatus:
        """Derive active/expired from expires_at, unless the source already
        asserted a terminal status (withdrawn/superseded) which always wins."""
        if self.status in (ValidityStatus.WITHDRAWN, ValidityStatus.SUPERSEDED):
            return self.status
        if self.expires_at is None:
            return ValidityStatus.NO_EXPIRY_STATED
        return ValidityStatus.ACTIVE if as_of < self.expires_at else ValidityStatus.EXPIRED


# ---------------------------------------------------------------------------
# Section 7: Review
# ---------------------------------------------------------------------------

@dataclass
class FieldMatch:
    field: str
    requirement_value: str
    quotation_value: str


@dataclass
class FieldDifference:
    field: str
    requirement_value: str
    quotation_value: str
    materiality: Materiality


@dataclass
class UnresolvedItem:
    field: str
    reason: str


@dataclass
class Review:
    matched_against_requirement_id: str
    confirmed_matches: List[FieldMatch] = field(default_factory=list)
    differences: List[FieldDifference] = field(default_factory=list)
    unresolved: List[UnresolvedItem] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Top-level record
# ---------------------------------------------------------------------------

@dataclass
class QuotationRecord:
    provenance: Provenance
    supplier: Supplier
    product: Product
    costs: Costs
    delivery: Delivery
    validity: Validity
    review: Optional[Review] = None

    def collect_unresolved_from_costs(self) -> List[UnresolvedItem]:
        """Surface cost-side unknowns as explicit unresolved items rather than
        letting them disappear into a default during ranking."""
        items: List[UnresolvedItem] = []
        if self.costs.tax_status == TaxStatus.UNKNOWN:
            items.append(UnresolvedItem(
                field="tax_status",
                reason="tax treatment unknown — excluded from cost ranking confidence",
            ))
        if self.costs.freight_amount is None:
            items.append(UnresolvedItem(
                field="freight_amount",
                reason="freight not stated — total_payable_amount may be incomplete",
            ))
        if self.delivery.commitment_type == CommitmentType.UNSPECIFIED:
            items.append(UnresolvedItem(
                field="delivery_commitment",
                reason="no delivery commitment stated",
            ))
        return items


# ---------------------------------------------------------------------------
# Implementation rule enforcement
# ---------------------------------------------------------------------------

# Only these source types may ever be shown as a "genuine quotation" result.
_COMPARISON_ELIGIBLE = {SourceType.GENUINE_QUOTATION, SourceType.SYNTHETIC}


def assert_usable_for_comparison(record: QuotationRecord) -> None:
    """
    Raises if a record must not feed the real quotation-comparison result.

    Awards, catalogs, and price registrations can validate schema *shape*
    (they parse into this structure fine) but must never be presented to a
    buyer as a quotation. Synthetic records may support the demo but must
    remain visibly labeled by the caller (this function does not render UI —
    it only gates data eligibility).
    """
    if record.provenance.source_type not in _COMPARISON_ELIGIBLE:
        raise ValueError(
            f"{record.provenance.record_id}: source_type="
            f"{record.provenance.source_type.value} cannot be presented as a "
            f"quotation-comparison result (schema-validation use only)"
        )
    if (
        record.provenance.source_type == SourceType.SYNTHETIC
        and record.provenance.real_or_synthetic != RealOrSynthetic.SYNTHETIC
    ):
        # Defensive — Provenance.__post_init__ already guarantees this, but the
        # comparison gate re-checks it since this is the highest-stakes boundary.
        raise ValueError(
            f"{record.provenance.record_id}: synthetic record missing synthetic label"
        )
