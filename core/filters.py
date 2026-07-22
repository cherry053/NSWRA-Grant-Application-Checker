"""Pure filtering logic for the criteria on the results view.

The checker handles one application at a time and stores nothing between
sessions, so filtering operates on the checked criteria of the current
application - not on a list of applications. Free of Streamlit imports so it
can be unit-tested directly.
"""

from core.models import CriterionResult

VALID_STATUSES: tuple[str, ...] = ("Pass", "Review", "Fail")


def criterion_status(criterion: CriterionResult) -> str:
    """Map a checked criterion onto its user-facing status.

    A criterion that passed is a "Pass"; a failed warning-severity criterion
    needs a human decision ("Review"); a failed critical criterion is a "Fail".
    """
    if criterion.passed:
        return "Pass"
    if criterion.severity == "warning":
        return "Review"
    return "Fail"


def section_status(criteria: list[CriterionResult]) -> str:
    """Overall status of one form section: the worst status among its criteria."""
    statuses = {criterion_status(criterion) for criterion in criteria}
    for status in ("Fail", "Review"):
        if status in statuses:
            return status
    return "Pass"


def filter_criteria(
    criteria: list[CriterionResult],
    statuses: set[str],
    search_term: str,
) -> list[CriterionResult]:
    """Return the criteria whose status is in `statuses` and that match `search_term`.

    Both conditions must hold (AND logic). The search term is matched
    case-insensitively as a substring of the criterion name, its form section,
    or its detail text; an empty or whitespace-only term matches everything.
    """
    term = search_term.strip().casefold()
    return [
        criterion
        for criterion in criteria
        if criterion_status(criterion) in statuses and _matches_search(criterion, term)
    ]


def status_counts(criteria: list[CriterionResult]) -> dict[str, int]:
    """Count criteria per status, with a zero entry for every valid status."""
    counts: dict[str, int] = {status: 0 for status in VALID_STATUSES}
    for criterion in criteria:
        counts[criterion_status(criterion)] += 1
    return counts


def _matches_search(criterion: CriterionResult, term: str) -> bool:
    if not term:
        return True
    return (
        term in criterion.name.casefold()
        or term in criterion.section.casefold()
        or term in criterion.detail.casefold()
    )
