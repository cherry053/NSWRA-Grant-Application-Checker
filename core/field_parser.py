from decimal import Decimal, InvalidOperation
from typing import Optional

from core.models import ApplicationData

RADIO_SELECTED = "◉"
RADIO_UNSELECTED = "○"
CHECKBOX_TICKED = "☑"
CHECKBOX_UNTICKED = "☐"

# Helper/guidance sentences that sit under a field label in the export. A line
# starting with one of these is never a field value.
GUIDANCE_PREFIXES = (
    "Must be",
    "Please ",
    "This is",
    "This field",
    "This refers",
    "e.g.",
    "E.g.",
    "Country code",
    "Provide the",
    "Briefly describe",
    "Applicants are",
    "Displays all",
    "We may contact",
    "Position held",
    "Represents the",
    "Classify the",
    "Re-damaged asset",
    "Estimate in",
    "Information from",
    "Information retrieved",
    "documentation such as",
    '"Estimated',
)


def _is_guidance(line: str) -> bool:
    return any(line.startswith(prefix) for prefix in GUIDANCE_PREFIXES)


def _value_after(lines: list[str], index: int) -> Optional[str]:
    """The line following a label, unless it is blank, guidance, or another widget."""
    if index + 1 >= len(lines):
        return None
    value = lines[index + 1].strip()
    if not value or _is_guidance(value) or value.endswith("*"):
        return None
    if RADIO_SELECTED in value or RADIO_UNSELECTED in value:
        return None
    return value


def _value_block(lines: list[str], index: int, stop_prefixes: tuple[str, ...], max_span: int = 4) -> Optional[str]:
    """Join the lines following a label until guidance/another field begins."""
    collected: list[str] = []
    for line in lines[index + 1 : index + 1 + max_span]:
        value = line.strip()
        if not value or _is_guidance(value) or value.endswith("*"):
            break
        if any(value.startswith(prefix) for prefix in stop_prefixes):
            break
        collected.append(value)
    return " ".join(collected) or None


def _inline_or_next(lines: list[str], index: int, label: str) -> Optional[str]:
    """Value on the same line as the label, falling back to the next line."""
    rest = lines[index][len(label):].strip()
    if rest and not _is_guidance(rest):
        return rest
    return _value_after(lines, index)


def _radio_selection(lines: list[str], index: int, window: int = 10) -> Optional[str]:
    """The option marked with a filled radio button in the lines at/after a question.

    Returns None when no option is selected (no filled marker in the window).
    """
    for line in lines[index : index + window]:
        if RADIO_SELECTED in line:
            after = line.split(RADIO_SELECTED, 1)[1]
            if RADIO_UNSELECTED in after:
                after = after.split(RADIO_UNSELECTED, 1)[0]
            return after.strip() or None
    return None


def _checkbox_state(lines: list[str], index: int, window: int = 5) -> Optional[bool]:
    """True/False for a ticked/unticked checkbox near a label, None if absent."""
    for line in lines[index : index + window]:
        if CHECKBOX_TICKED in line:
            return True
        if CHECKBOX_UNTICKED in line:
            return False
    return None


def parse_currency(text: str) -> Optional[Decimal]:
    """'$3,600,000.00' -> Decimal('3600000.00'), or None when not an amount."""
    cleaned = text.strip().replace("$", "").replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def parse_application_header(pages: list[list[str]]) -> dict[str, Optional[str]]:
    """Pull the application number and applicant from the repeated page header."""
    meta: dict[str, Optional[str]] = {"application_id": None, "applicant_name": None}
    for page in pages:
        for line in page[:4]:
            if line.startswith("Application No."):
                rest = line[len("Application No."):].strip()
                if " From " in rest:
                    app_id, applicant = rest.split(" From ", 1)
                    meta["application_id"] = app_id.strip()
                    if " - " in applicant:
                        applicant = applicant.rsplit(" - ", 1)[0]
                    meta["applicant_name"] = applicant.strip() or None
                else:
                    meta["application_id"] = rest.split()[0] if rest else None
                return meta
    return meta


def parse_pre_table_fields(lines: list[str], data: ApplicationData) -> ApplicationData:
    """Fill application fields that appear before the damage table."""
    for i, line in enumerate(lines):
        if "I confirm that I have read and understood" in line:
            data.eligibility_confirmed = _checkbox_state(lines, i)
        elif line == "Organisation Name *":
            data.organisation_name = _value_after(lines, i)
        elif line == "Primary Address *":
            data.primary_address = _value_block(lines, i, stop_prefixes=("Latitude:",))
        elif line == "Postal Address *":
            data.postal_address = _value_block(lines, i, stop_prefixes=("Latitude:",))
        elif line == "Primary Phone Number *":
            data.primary_phone = _value_after(lines, i)
        elif line == "Email Address *":
            data.email_address = _value_after(lines, i)
        elif line == "Primary Contact *":
            data.primary_contact = _value_after(lines, i)
        elif line == "Primary Contact Position *":
            data.primary_contact_position = _value_after(lines, i)
        elif line == "Primary Contact Phone Number *":
            data.primary_contact_phone = _value_after(lines, i)
        elif line == "Primary Contact Email *":
            data.primary_contact_email = _value_after(lines, i)
        elif line.startswith("Does the applicant have an Australian Business Number"):
            data.has_abn = _radio_selection(lines, i, window=4)
        elif line == "ABN *":
            data.abn = _value_after(lines, i)
        elif "willing to obtain $20 million in public liability insurance?" in line:
            data.insurance_answer = _radio_selection(lines, i, window=4)
        elif line.startswith("Please provide evidence that the applicant organisation holds"):
            for follower in lines[i : i + 8]:
                if follower.startswith("Filename:"):
                    data.insurance_evidence_file = follower.split(":", 1)[1].strip() or None
                    break
        elif line == "Title *":
            data.title = _value_block(lines, i, stop_prefixes=())
        elif line == "Brief description *":
            data.brief_description = _value_block(lines, i, stop_prefixes=(), max_span=6)
        elif line == "Anticipated start date *":
            data.start_date = _value_after(lines, i)
        elif line == "Anticipated end date *":
            data.end_date = _value_after(lines, i)
        elif line == "Primary location of your initiative *":
            data.primary_initiative_location = _value_block(lines, i, stop_prefixes=("Latitude:",))
        elif line == "Predominant NSW LGA *":
            data.predominant_lga = _value_after(lines, i)
        elif line == "State Electorate *":
            data.state_electorate = _value_after(lines, i)
        elif line == "Federal Electorate *":
            data.federal_electorate = _value_after(lines, i)
        elif line == "Predominant Asset Type *":
            data.predominant_asset_type = _radio_selection(lines, i, window=12)
        elif line.startswith("Is this a re-damaged asset?"):
            data.re_damaged_answer = _radio_selection(lines, i, window=4)
    return data


def parse_post_table_fields(lines: list[str], data: ApplicationData) -> ApplicationData:
    """Fill application fields that appear after the damage table."""
    for i, line in enumerate(lines):
        if line.startswith("Number of damaged items being restored"):
            value = _value_after(lines, i)
            if value and value.isdigit():
                data.declared_item_count = int(value)
        elif line.startswith("Total Amount Requested"):
            if "$" in line:
                data.total_amount_requested = parse_currency("$" + line.split("$", 1)[1])
            else:
                for follower in lines[i + 1 : i + 5]:
                    if follower.strip().startswith("$"):
                        data.total_amount_requested = parse_currency(follower)
                        break
        elif "damaged items listed in this EPAR application?" in line:
            data.insurance_compensation_answer = _radio_selection(lines, i, window=4)
        elif line.startswith("I agree *"):
            data.declaration_agreed = _checkbox_state(lines, i, window=3)
        elif line.startswith("Name of authorised"):
            data.authoriser_name = _authoriser_name(lines, i)
        elif line.startswith("Position *"):
            data.authoriser_position = _inline_or_next(lines, i, "Position *")
        elif line.startswith("Phone number *"):
            data.authoriser_phone = _inline_or_next(lines, i, "Phone number *")
        elif line.startswith("Email *"):
            data.authoriser_email = _inline_or_next(lines, i, "Email *")
    return data


def _authoriser_name(lines: list[str], index: int) -> Optional[str]:
    """Recover the authoriser name from the two-column declaration layout.

    The export merges label and guidance columns: 'Name of authorised <value?>
    Must be a senior staff member...' with the label continuing on the next
    line as 'person * ... authorised volunteer'.
    """
    parts: list[str] = []
    first = lines[index][len("Name of authorised"):].strip()
    if "Must be a senior" in first:
        first = first.split("Must be a senior", 1)[0].strip()
    if first and not _is_guidance(first):
        parts.append(first)

    if index + 1 < len(lines):
        second = lines[index + 1].strip()
        if second.startswith("person *"):
            second = second[len("person *"):].strip()
            if second.endswith("authorised volunteer"):
                second = second[: -len("authorised volunteer")].strip()
            if second and not _is_guidance(second):
                parts.append(second)

    return " ".join(parts) or None
