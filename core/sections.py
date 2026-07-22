"""The six form-navigation sections of the EPAR application, used to group criteria."""

from core.models import CriterionResult

SECTION_GRANT_PROGRAM = "1. Grant Program Information (EPAR)"
SECTION_AGENCY = "2. Eligible Delivery Agency Details"
SECTION_PROJECT = "3. EPAR Project Details"
SECTION_DAMAGE = "4. Damage Information"
SECTION_FUNDING = "5. EPAR Funding Request"
SECTION_DECLARATION = "6. Declaration and Authorisation"

FORM_SECTIONS = (
    SECTION_GRANT_PROGRAM,
    SECTION_AGENCY,
    SECTION_PROJECT,
    SECTION_DAMAGE,
    SECTION_FUNDING,
    SECTION_DECLARATION,
)


def stamp_section(section: str, checks: list[CriterionResult]) -> list[CriterionResult]:
    """Assign every check in the list to a form section, returning the same list."""
    for check in checks:
        check.section = section
    return checks


def group_by_section(criteria: list[CriterionResult]) -> dict[str, list[CriterionResult]]:
    """Group criteria by form section, in form-navigation order.

    Criteria carrying an unknown section label are appended after the six
    known sections so nothing silently disappears from a report.
    """
    groups: dict[str, list[CriterionResult]] = {section: [] for section in FORM_SECTIONS}
    for criterion in criteria:
        groups.setdefault(criterion.section or "Other", []).append(criterion)
    return {section: checks for section, checks in groups.items() if checks}


def section_passed_counts(checks: list[CriterionResult]) -> tuple[int, int]:
    """(passed, total) for one section's criteria."""
    return sum(1 for check in checks if check.passed), len(checks)
