from datetime import datetime
from decimal import Decimal
from typing import Optional

from core.models import ApplicationData, CheckResult, CriterionResult, DamageItem
from core.sections import (
    SECTION_AGENCY,
    SECTION_DAMAGE,
    SECTION_DECLARATION,
    SECTION_FUNDING,
    SECTION_GRANT_PROGRAM,
    SECTION_PROJECT,
    stamp_section,
)

DATE_FORMAT = "%d/%m/%Y"

# Words and phrases that may indicate costs that are not eligible for disaster
# restoration funding. These are flagged as amber (Review) rather than red
# (Fail) because eligibility can sometimes be confirmed if there is sufficient
# evidence that the expense is directly associated with restoration works.
AMBER_INELIGIBILITY_KEYWORDS = [
    "cleanup",
    "cleaning debris",
    "routine clean up",
    "park clean up",
    "green waste removal",
    "green waste disposal",
    "vegetation clearance",
    "tree management",
    "landscape restoration",
    "arboricultural services",
    "hazard reduction",
    "bushland restoration",
    "environmental restoration",
    "land rehabilitation",
    "revegetation",
    "enhancement planting",
    "ecological works",
    "stabilisation works",
    "remediation",
    "maintenance activities",
    "routine maintenance",
    "ongoing maintenance",
    "defect correction",
    "preventative works",
    "upgrade to current standards",
    "capacity increase",
    "expansion works",
    "additional functionality",
    "asset improvement",
    "betterment opportunity",
    "renewal works",
    "deferred maintenance",
    "defect rectification",
    "future-proofing",
    "general maintenance",
    "operational expenditure",
    "administrative support",
    "new works",
    "enhancement",
    "modernisation",
    "beautification",
    "redevelopment",
    "memorials",
    "legal disputes",
    "interest charges",
    "plant replacement",
    "vehicles",
    "upgrade",
    "betterment",
    "new asset",
    "expansion",
    "pre-existing damage",
    "wear and tear",
    "asset renewal",
    "lifecycle replacement",
    "operational costs",
    "administration overheads",
    "internal overhead recovery",
    "contents replacement",
    "insurance excess",
    "uninsured loss",
    "penalties",
    "fines",
    "land acquisition",
    "religious facilities",
    "strategic project",
    "amenity improvements",
]

# Coordinate bounds stated on the form for damage locations within NSW.
LONGITUDE_MIN, LONGITUDE_MAX = 140.902254, 153.730439
LATITUDE_MIN, LATITUDE_MAX = -37.633837, -28.592358

MAX_TITLE_WORDS = 25
MAX_DESCRIPTION_WORDS = 50
MAX_DAMAGE_ITEMS = 50
MAX_UPLOAD_BYTES = 100 * 1_000_000
ITR_THRESHOLD = Decimal("25000000")

PRE_DISASTER_EVIDENCE_SUFFIX = "predisasterevidence"
DAMAGE_EVIDENCE_SUFFIX = "damageevidence"


def _problem_sentence(problems: list[str]) -> str:
    text = "; ".join(problems) + "."
    return text[0].upper() + text[1:]


def _parse_date(value: Optional[str]):
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), DATE_FORMAT).date()
    except ValueError:
        return None


def _is_valid_email(value: str) -> bool:
    if " " in value or value.count("@") != 1:
        return False
    local, _, domain = value.partition("@")
    return bool(local) and "." in domain and not domain.startswith(".") and not domain.endswith(".")


def _is_australian_phone(value: str) -> bool:
    cleaned = value
    for junk in (" ", "(", ")", "-"):
        cleaned = cleaned.replace(junk, "")
    if cleaned.startswith("+61"):
        cleaned = "0" + cleaned[3:]
    return cleaned.isdigit() and len(cleaned) == 10 and cleaned.startswith("0")


def _provided(name: str, value: Optional[str], severity: str = "critical") -> CriterionResult:
    passed = bool(value and value.strip())
    detail = f"Value: '{value}'." if passed else "Required field is missing or empty."
    return CriterionResult(name, passed, severity, detail)


def _email_check(name: str, value: Optional[str]) -> CriterionResult:
    if not value:
        return CriterionResult(name, False, "critical", "Required email address is missing.")
    passed = _is_valid_email(value)
    detail = f"Email '{value}' looks valid." if passed else f"Email '{value}' is not a valid address."
    return CriterionResult(name, passed, "critical", detail)


def _phone_check(name: str, value: Optional[str]) -> CriterionResult:
    if not value:
        return CriterionResult(name, False, "critical", "Required phone number is missing.")
    passed = _is_australian_phone(value)
    detail = (
        f"Phone number '{value}' looks like an Australian number."
        if passed
        else f"Phone number '{value}' is not a valid Australian number."
    )
    return CriterionResult(name, passed, "critical", detail)


def _nsw_check(name: str, value: Optional[str]) -> CriterionResult:
    if not value:
        return CriterionResult(name, False, "critical", "Required address/location is missing.")
    passed = "NSW" in value
    detail = f"'{value}' is in NSW." if passed else f"'{value}' is not in NSW."
    return CriterionResult(name, passed, "critical", detail)


def _word_limit_check(name: str, value: Optional[str], limit: int) -> CriterionResult:
    if not value:
        return CriterionResult(name, False, "critical", "Required field is missing or empty.")
    words = len(value.split())
    passed = words <= limit
    detail = f"{words} word(s), within the {limit}-word limit." if passed else f"{words} word(s) exceeds the {limit}-word limit."
    return CriterionResult(name, passed, "critical", detail)


def application_checks(data: ApplicationData) -> list[CriterionResult]:
    checks = stamp_section(
        SECTION_GRANT_PROGRAM,
        [
            CriterionResult(
                "Eligibility Confirmation Ticked",
                data.eligibility_confirmed is True,
                "critical",
                "Eligibility confirmation checkbox is ticked."
                if data.eligibility_confirmed
                else "The eligibility confirmation checkbox is not ticked.",
            ),
        ],
    )

    agency_checks = [
        _provided("Organisation Name Provided", data.organisation_name),
        _nsw_check("Primary Address Within NSW", data.primary_address),
        _nsw_check("Postal Address Within NSW", data.postal_address),
        _phone_check("Primary Phone Valid", data.primary_phone),
        _email_check("Email Address Valid", data.email_address),
        _provided("Primary Contact Provided", data.primary_contact),
        _provided("Primary Contact Position Provided", data.primary_contact_position),
        _phone_check("Primary Contact Phone Valid", data.primary_contact_phone),
        _email_check("Primary Contact Email Valid", data.primary_contact_email),
    ]

    if data.has_abn == "Yes":
        agency_checks.append(_provided("ABN Provided", data.abn))
    else:
        agency_checks.append(
            CriterionResult(
                "ABN Question Answered",
                data.has_abn is not None,
                "critical",
                f"Answer: '{data.has_abn}'." if data.has_abn else "The ABN question is unanswered.",
            )
        )

    agency_checks.extend(
        [
            CriterionResult(
                "Public Liability Insurance Answered",
                data.insurance_answer is not None,
                "critical",
                f"Answer: '{data.insurance_answer}'."
                if data.insurance_answer
                else "The public liability insurance question is unanswered.",
            ),
            _provided("Insurance Evidence Attached", data.insurance_evidence_file),
        ]
    )
    checks.extend(stamp_section(SECTION_AGENCY, agency_checks))

    checks.extend(
        stamp_section(
            SECTION_PROJECT,
            [
                _word_limit_check("Project Title Within Word Limit", data.title, MAX_TITLE_WORDS),
                _word_limit_check(
                    "Brief Description Within Word Limit", data.brief_description, MAX_DESCRIPTION_WORDS
                ),
                _date_range_check(data),
                _nsw_check("Primary Initiative Location Within NSW", data.primary_initiative_location),
                _provided("Predominant NSW LGA Provided", data.predominant_lga),
                _provided("State Electorate Provided", data.state_electorate),
                _provided("Federal Electorate Provided", data.federal_electorate),
                _provided("Predominant Asset Type Selected", data.predominant_asset_type),
                _provided("Re-damaged Asset Question Answered", data.re_damaged_answer),
            ],
        )
    )

    checks.extend(
        stamp_section(
            SECTION_FUNDING,
            [
                CriterionResult(
                    "Total Amount Requested Provided",
                    data.total_amount_requested is not None,
                    "critical",
                    f"Total amount requested: ${data.total_amount_requested:,.2f}."
                    if data.total_amount_requested is not None
                    else "No total amount requested found.",
                ),
                CriterionResult(
                    "Insurance Compensation Question Answered",
                    data.insurance_compensation_answer is not None,
                    "critical",
                    f"Answer: '{data.insurance_compensation_answer}'."
                    if data.insurance_compensation_answer
                    else "The insurance compensation question is unanswered.",
                ),
            ],
        )
    )

    checks.extend(
        stamp_section(
            SECTION_DECLARATION,
            [
                CriterionResult(
                    "Declaration Agreed",
                    data.declaration_agreed is True,
                    "critical",
                    "The declaration checkbox is ticked."
                    if data.declaration_agreed
                    else "The declaration 'I agree' checkbox is not ticked.",
                ),
                _provided("Authoriser Name Provided", data.authoriser_name),
                _provided("Authoriser Position Provided", data.authoriser_position),
                _phone_check("Authoriser Phone Valid", data.authoriser_phone),
                _email_check("Authoriser Email Valid", data.authoriser_email),
            ],
        )
    )
    return checks


def _date_range_check(data: ApplicationData) -> CriterionResult:
    name = "Start Date Before End Date"
    start = _parse_date(data.start_date)
    end = _parse_date(data.end_date)
    if start is None or end is None:
        return CriterionResult(
            name, False, "critical", f"Could not read dates '{data.start_date}' / '{data.end_date}'."
        )
    passed = start <= end
    detail = f"{start} to {end} is a valid range." if passed else f"Start date {start} is after end date {end}."
    return CriterionResult(name, passed, "critical", detail)


def _item_required_fields(item: DamageItem, label: str) -> CriterionResult:
    required = {
        "Damage Item ID": item.damage_item_id,
        "Asset ID": item.asset_id,
        "Asset Name": item.asset_name,
        "Date Asset Accessible": item.date_accessible,
        # "Asset Sub-Category": item.sub_category,
        "Asset Capacity": item.capacity,
        "Asset Layout": item.layout,
        # "Asset Dimensions": item.dimensions,
        "Damage Description": item.damage_description,
        "Estimation Method": item.estimation_method,
        "Pre-Disaster Evidence": item.pre_disaster_evidence_file,
        "Damage Evidence": item.damage_evidence_file,
        "Cost Estimation Evidence": item.cost_evidence_file,
        "Cost Estimation Methodology": item.methodology,
        "Total Damage Estimate": item.cost_total,
    }
    missing = [field for field, value in required.items() if value in (None, "")]
    passed = not missing
    detail = "All required fields present." if passed else f"Missing field(s): {', '.join(missing)}."
    return CriterionResult(f"{label} - Required Fields Present", passed, "critical", detail)


def _item_date_check(item: DamageItem, label: str) -> CriterionResult:
    name = f"{label} - Accessible Date Valid"
    parsed = _parse_date(item.date_accessible)
    passed = parsed is not None
    detail = f"Date '{item.date_accessible}' is valid." if passed else f"Date '{item.date_accessible}' is not a valid dd/mm/yyyy date."
    return CriterionResult(name, passed, "critical", detail)


def _item_locations_check(item: DamageItem, label: str) -> CriterionResult:
    name = f"{label} - Damage Locations Within NSW"
    problems = []
    for kind, value in (("start", item.location_start), ("end", item.location_end)):
        if not value:
            problems.append(f"{kind} location is missing")
        elif "NSW" not in value:
            problems.append(f"{kind} location '{value}' is not in NSW")
    passed = not problems
    detail = "Start and end damage locations are in NSW." if passed else _problem_sentence(problems)
    return CriterionResult(name, passed, "critical", detail)


def _item_coordinates_check(item: DamageItem, label: str) -> CriterionResult:
    name = f"{label} - Coordinates Within NSW Bounds"
    coordinates = {
        "Longitude (from)": (item.longitude_from, LONGITUDE_MIN, LONGITUDE_MAX),
        "Latitude (from)": (item.latitude_from, LATITUDE_MIN, LATITUDE_MAX),
        "Longitude (to)": (item.longitude_to, LONGITUDE_MIN, LONGITUDE_MAX),
        "Latitude (to)": (item.latitude_to, LATITUDE_MIN, LATITUDE_MAX),
    }
    problems = []
    for field, (value, low, high) in coordinates.items():
        if value is None:
            problems.append(f"{field} is missing")
        elif not low <= value <= high:
            problems.append(f"{field} {value} is outside {low} to {high}")
    passed = not problems
    detail = "All four coordinates are within the NSW bounds." if passed else _problem_sentence(problems)
    return CriterionResult(name, passed, "critical", detail)


def _item_cost_check(item: DamageItem, label: str) -> CriterionResult:
    name = f"{label} - Cost Components Sum To Total"
    components = (item.cost_construction, item.cost_pm_design, item.cost_contingency, item.cost_escalation)
    if any(value is None for value in components) or item.cost_total is None:
        return CriterionResult(name, False, "critical", "One or more cost amounts are missing.")
    total = sum(components)
    passed = total == item.cost_total
    detail = (
        f"Components sum to ${total:,.2f}, matching the stated total."
        if passed
        else f"Components sum to ${total:,.2f} but the stated total is ${item.cost_total:,.2f}."
    )
    return CriterionResult(name, passed, "critical", detail)


def _expected_evidence_name(damage_id: str, filename: str, expected_suffix: str) -> Optional[str]:
    """None when the filename follows '<DamageID>_<ExpectedSuffix>.<ext>', else the problem."""
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    # The suffix never contains an underscore but a damage item ID may, so the
    # split anchors on the last underscore rather than the first.
    prefix, separator, suffix = stem.rpartition("_")
    if not separator:
        return f"'{filename}' has no underscore separator"
    if prefix != damage_id:
        return f"'{filename}' does not start with '{damage_id}_'"
    if suffix.lower() != expected_suffix:
        return f"'{filename}' does not end with '{expected_suffix}' before the extension"
    return None


def _item_naming_check(item: DamageItem, label: str) -> CriterionResult:
    name = f"{label} - Evidence File Naming Convention"
    if not item.damage_item_id:
        return CriterionResult(name, False, "warning", "Cannot verify file names without a damage item ID.")
    problems = []
    for filename, suffix in (
        (item.pre_disaster_evidence_file, PRE_DISASTER_EVIDENCE_SUFFIX),
        (item.damage_evidence_file, DAMAGE_EVIDENCE_SUFFIX),
    ):
        if not filename:
            problems.append("an evidence file is missing")
            continue
        problem = _expected_evidence_name(item.damage_item_id, filename, suffix)
        if problem:
            problems.append(problem)
    passed = not problems
    detail = (
        "Evidence file names follow the DamageID_PredisasterEvidence / DamageID_DamageEvidence convention."
        if passed
        else _problem_sentence(problems)
    )
    return CriterionResult(name, passed, "warning", detail)


def _item_file_size_check(item: DamageItem, label: str) -> CriterionResult:
    name = f"{label} - Upload Sizes Within 100MB"
    uploads = {
        "pre-disaster evidence": item.pre_disaster_evidence_bytes,
        "damage evidence": item.damage_evidence_bytes,
        "cost evidence": item.cost_evidence_bytes,
    }
    oversized = [
        f"{kind} is {size / 1_000_000:.1f} MB" for kind, size in uploads.items() if size and size > MAX_UPLOAD_BYTES
    ]
    passed = not oversized
    detail = "All uploads are within the 100MB limit." if passed else _problem_sentence(oversized)
    return CriterionResult(name, passed, "warning", detail)


def _item_ineligibility_keyword_check(item: DamageItem, label: str) -> CriterionResult:
    name = f"{label} - Potentially Ineligible Cost Description"

    # Combine the free-text fields into one block of text to search through.
    fields = [
        item.damage_description,
        item.estimation_method,
        item.methodology,
        item.asset_name,
    ]
    combined_text = ""
    for field in fields:
        if field is not None:
            combined_text = combined_text + " " + field
    combined_text = combined_text.lower()

    # Check each keyword against the combined text.
    matched_keywords = []
    for keyword in AMBER_INELIGIBILITY_KEYWORDS:
        if keyword in combined_text:
            matched_keywords.append(keyword)

    # Keep only the most specific phrase when matches overlap: a description
    # containing "upgrade to current standards" also contains "upgrade", and
    # repeating the shorter keyword would flag the same text twice.
    matched_keywords = [
        keyword
        for keyword in matched_keywords
        if not any(keyword != other and keyword in other for other in matched_keywords)
    ]

    if len(matched_keywords) == 0:
        return CriterionResult(name, True, "warning", "No potentially ineligible cost keywords detected.")

    keyword_list = ", ".join(matched_keywords)
    detail = (
        "The following terms may indicate costs that are not eligible for disaster restoration "
        "funding: " + keyword_list + ". "
        "Eligibility could be assessed if there is sufficient evidence that the expense is "
        "associated with restoration works."
    )
    return CriterionResult(name, False, "warning", detail)


def damage_item_checks(item: DamageItem, position: int) -> list[CriterionResult]:
    label = item.damage_item_id or f"Item {position}"
    return stamp_section(
        SECTION_DAMAGE,
        [
            _item_required_fields(item, label),
            _item_date_check(item, label),
            _item_locations_check(item, label),
            _item_coordinates_check(item, label),
            _item_cost_check(item, label),
            _item_naming_check(item, label),
            _item_file_size_check(item, label),
            _item_ineligibility_keyword_check(item, label),
        ],
    )


def cross_checks(
    data: ApplicationData, items: list[DamageItem], table_warnings: list[str]
) -> list[CriterionResult]:
    declared = data.declared_item_count
    parsed = len(items)

    damage_checks = [
        CriterionResult(
            "Damage Item Count Reconciles",
            declared == parsed and declared is not None,
            "critical",
            f"PDF declares {declared} damage item(s); the table text yielded {parsed}."
            if declared is not None
            else f"The PDF does not declare a damage item count; the table text yielded {parsed}.",
        ),
        CriterionResult(
            "Damage Item Limit",
            parsed <= MAX_DAMAGE_ITEMS,
            "critical",
            f"{parsed} damage item(s), within the {MAX_DAMAGE_ITEMS}-item limit."
            if parsed <= MAX_DAMAGE_ITEMS
            else f"{parsed} damage item(s) exceeds the {MAX_DAMAGE_ITEMS}-item limit.",
        ),
        CriterionResult(
            "Damage Table Parsed Cleanly",
            not table_warnings,
            "warning",
            "The damage table text parsed without warnings."
            if not table_warnings
            else f"{len(table_warnings)} parse warning(s): " + "; ".join(table_warnings[:6]) + ("..." if len(table_warnings) > 6 else ""),
        ),
    ]

    totals = [item.cost_total for item in items if item.cost_total is not None]
    items_total = sum(totals, Decimal("0"))
    if data.total_amount_requested is None:
        reconcile = CriterionResult(
            "Total Amount Requested Reconciles",
            False,
            "critical",
            f"No total in the PDF to reconcile; table items sum to ${items_total:,.2f}.",
        )
    else:
        passed = items_total == data.total_amount_requested
        reconcile = CriterionResult(
            "Total Amount Requested Reconciles",
            passed,
            "critical",
            f"PDF declares ${data.total_amount_requested:,.2f} and table items sum to ${items_total:,.2f}."
            if passed
            else f"Mismatch: PDF declares ${data.total_amount_requested:,.2f} but table items sum to ${items_total:,.2f}.",
        )

    package_total = data.total_amount_requested if data.total_amount_requested is not None else items_total
    funding_checks = [
        reconcile,
        CriterionResult(
            "Independent Technical Review Threshold",
            package_total <= ITR_THRESHOLD,
            "warning",
            f"Package total ${package_total:,.2f} is under the $25M ITR threshold."
            if package_total <= ITR_THRESHOLD
            else f"Package total ${package_total:,.2f} exceeds $25M and will trigger an Independent Technical Review.",
        ),
    ]

    return stamp_section(SECTION_DAMAGE, damage_checks) + stamp_section(SECTION_FUNDING, funding_checks)


def selection_notices(items: list[DamageItem]) -> list[str]:
    """User-facing double-check disclaimers for selections the export cannot show.

    Identical notes from different damage items are grouped into one notice
    listing every affected item, so the Active Flags panel shows one card per
    limitation instead of one per item.
    """
    affected: dict[str, list[str]] = {}
    for position, item in enumerate(items, start=1):
        label = item.damage_item_id or f"Item {position}"
        for note in item.parse_notes:
            affected.setdefault(note, []).append(label)
    return [
        f"{note} Please double-check this selection in SmartyGrants before "
        f"submitting. Affected item(s): {', '.join(labels)}."
        for note, labels in affected.items()
    ]


def run_checks(
    data: ApplicationData,
    items: Optional[list[DamageItem]] = None,
    table_warnings: Optional[list[str]] = None,
) -> CheckResult:
    items = items or []
    criteria = application_checks(data)
    for position, item in enumerate(items, start=1):
        criteria.extend(damage_item_checks(item, position))
    criteria.extend(cross_checks(data, items, table_warnings or []))

    passed_count = sum(1 for criterion in criteria if criterion.passed)
    confidence_score = round(100 * passed_count / len(criteria)) if criteria else 0

    critical_failures = any(not c.passed and c.severity == "critical" for c in criteria)
    if passed_count == len(criteria):
        overall_status = "PASS"
    elif critical_failures and passed_count <= len(criteria) // 2:
        overall_status = "FAIL"
    else:
        overall_status = "PARTIAL"

    return CheckResult(
        overall_status=overall_status,
        confidence_score=confidence_score,
        criteria=criteria,
        damage_items=items,
        notices=selection_notices(items),
    )
