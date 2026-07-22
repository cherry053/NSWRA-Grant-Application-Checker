from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal, Optional


@dataclass
class ApplicationData:
    """Application-level fields parsed from the PDF (everything outside the damage table)."""

    # Eligibility
    eligibility_confirmed: Optional[bool] = None

    # Organisation details
    organisation_name: Optional[str] = None
    primary_address: Optional[str] = None
    postal_address: Optional[str] = None
    primary_phone: Optional[str] = None
    email_address: Optional[str] = None

    # Primary contact
    primary_contact: Optional[str] = None
    primary_contact_position: Optional[str] = None
    primary_contact_phone: Optional[str] = None
    primary_contact_email: Optional[str] = None

    # ABN
    has_abn: Optional[str] = None
    abn: Optional[str] = None

    # Public liability insurance
    insurance_answer: Optional[str] = None
    insurance_evidence_file: Optional[str] = None

    # Project details
    title: Optional[str] = None
    brief_description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    primary_initiative_location: Optional[str] = None
    predominant_lga: Optional[str] = None
    state_electorate: Optional[str] = None
    federal_electorate: Optional[str] = None
    predominant_asset_type: Optional[str] = None
    re_damaged_answer: Optional[str] = None

    # Post-table: totals and reconciliation
    declared_item_count: Optional[int] = None
    total_amount_requested: Optional[Decimal] = None
    insurance_compensation_answer: Optional[str] = None

    # Declaration and authorisation
    declaration_agreed: Optional[bool] = None
    authoriser_name: Optional[str] = None
    authoriser_position: Optional[str] = None
    authoriser_phone: Optional[str] = None
    authoriser_email: Optional[str] = None


@dataclass
class DamageItem:
    """One damage line item parsed from the pasted damage-table text export."""

    damage_item_id: Optional[str] = None
    asset_id: Optional[str] = None
    asset_name: Optional[str] = None
    date_accessible: Optional[str] = None

    location_start: Optional[str] = None
    location_end: Optional[str] = None

    longitude_from: Optional[float] = None
    latitude_from: Optional[float] = None
    longitude_to: Optional[float] = None
    latitude_to: Optional[float] = None

    sub_category: Optional[str] = None
    capacity: Optional[str] = None
    layout: Optional[str] = None
    dimensions: Optional[str] = None

    pre_disaster_evidence_file: Optional[str] = None
    pre_disaster_evidence_bytes: Optional[int] = None
    damage_evidence_file: Optional[str] = None
    damage_evidence_bytes: Optional[int] = None

    damage_description: Optional[str] = None
    estimation_method: Optional[str] = None

    cost_construction: Optional[Decimal] = None
    cost_pm_design: Optional[Decimal] = None
    cost_contingency: Optional[Decimal] = None
    cost_escalation: Optional[Decimal] = None
    cost_total: Optional[Decimal] = None

    cost_evidence_file: Optional[str] = None
    cost_evidence_bytes: Optional[int] = None
    methodology: Optional[str] = None

    # Genuine parse problems (e.g. a truncated record); these fail the
    # "Damage Table Parsed Cleanly" criterion.
    parse_warnings: list[str] = field(default_factory=list)
    # Known limitations of the text export (selections it cannot show); these
    # become informational notices asking the user to double-check manually,
    # and never count against the check result.
    parse_notes: list[str] = field(default_factory=list)


@dataclass
class CriterionResult:
    name: str
    passed: bool
    severity: Literal["critical", "warning"]
    detail: str
    section: str = ""


@dataclass
class CheckResult:
    overall_status: Literal["PASS", "FAIL", "PARTIAL"]
    confidence_score: int
    criteria: list[CriterionResult] = field(default_factory=list)
    damage_items: list[DamageItem] = field(default_factory=list)

    # Header metadata for the results page
    application_id: Optional[str] = None
    applicant_name: Optional[str] = None
    scanned_at: Optional[str] = None

    # Informational disclaimers about selections the text export cannot show,
    # rendered as INFO cards under Active Flags; they never affect the
    # confidence score or the overall status.
    notices: list[str] = field(default_factory=list)
    total_requested: Optional[Decimal] = None
