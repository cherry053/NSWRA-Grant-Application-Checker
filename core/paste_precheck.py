"""Upload-time screening of the pasted damage-table text.

When the applicant pastes the damage table into the upload form, only part of
it may have been copied. This module compares the number of complete records
in the pasted text against the item count the PDF itself declares, so the
upload page can warn the user before running the full analysis. It
deliberately does *not* score field-level extraction quality - that is
surfaced through the normal validation criteria on the results page.

Alongside the count comparison the same screening flags the other paste
mistakes seen in practice: an empty paste, more than one table pasted in
(a repeated header row, duplicated damage item IDs, or more records than the
PDF declares), and a record cut off part-way through. Expected column labels
absent from the paste are still checked, but reported as informational notes
rather than warnings: copying the filled-in table without its header row is
routine and harmless, so it never holds a submission back.

The PDF is scanned here *and* parsed again by the pipeline. That double read
is deliberate: the scan only walks the extracted text for one label, and it
is far cheaper than letting the applicant sit through a full analysis of an
incomplete paste.
"""

import io
import logging
from dataclasses import dataclass
from typing import Optional, Union

from core.damage_table_parser import parse_damage_table
from core.models import DamageItem
from core.pdf_extract import clean_lines, extract_pages

logger = logging.getLogger(__name__)

# Label of the PDF field stating how many damage items the application holds
# (the same anchor core.field_parser uses for the results-page reconciliation).
DECLARED_COUNT_LABEL = "Number of damaged items being restored"

# How many lines after the label may hold its value; the export places the
# value on the next line, occasionally after a guidance sentence.
_DECLARED_COUNT_WINDOW = 5

# Column labels every damage-table export carries. These are the same display
# names the validators and the damage-table parser anchor on, so a paste that
# lacks one of them is missing a column the checker relies on.
EXPECTED_COLUMN_LABELS = (
    "Asset Category",
    "Damage Item ID",
    "Asset ID",
    "Asset Name",
    "Date Asset Accessible",
    "Asset Sub-Category",
    "Asset Material",
    "Damage Description",
)

# A pasted table's header row names at least these two columns on one line;
# seeing that line more than once means more than one table was pasted in.
_HEADER_ROW_MARKERS = ("Asset Category", "Damage Item ID")


@dataclass
class PastePrecheckReport:
    """Outcome of screening one paste against one PDF, ready for the upload page."""

    declared_count: Optional[int]  # item count the PDF declares, None when absent
    record_count: int  # records found in the paste, complete or not
    complete_count: int  # records with an ID and a trailing total cost
    duplicate_ids: list[str]  # damage item IDs appearing more than once
    header_row_count: int  # table header rows found in the paste
    missing_columns: list[str]  # expected column labels absent from the paste
    warnings: list[str]  # user-facing sentences, one per problem found
    notes: list[str]  # informational sentences that never block a submission

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)


def _is_complete_record(item: DamageItem) -> bool:
    """A record is complete when it carries an ID and reaches its cost block.

    The cost amounts sit at the tail of every record, so a paste that stops
    part-way through a record loses them - which makes the missing total a
    reliable truncation signal without judging any other field.
    """
    return bool(item.damage_item_id) and item.cost_total is not None


def duplicate_item_ids(items: list[DamageItem]) -> list[str]:
    """Damage item IDs used by more than one record, in first-seen order."""
    counts: dict[str, int] = {}
    for item in items:
        if item.damage_item_id:
            counts[item.damage_item_id] = counts.get(item.damage_item_id, 0) + 1
    return [item_id for item_id, count in counts.items() if count > 1]


def count_header_rows(text: str) -> int:
    """How many lines of the paste look like the table's column header row."""
    lowered_markers = [marker.lower() for marker in _HEADER_ROW_MARKERS]
    return sum(
        1
        for line in text.splitlines()
        if all(marker in line.lower() for marker in lowered_markers)
    )


def missing_column_labels(text: str) -> list[str]:
    """Expected column labels that appear nowhere in the pasted text."""
    lowered = text.lower()
    return [label for label in EXPECTED_COLUMN_LABELS if label.lower() not in lowered]


def declared_count_from_lines(lines: list[str]) -> Optional[int]:
    """The declared damage item count, read from cleaned PDF lines.

    Scans for the label line, then takes the first purely numeric line in the
    short window after it; guidance sentences in between are skipped.
    """
    for index, line in enumerate(lines):
        if not line.startswith(DECLARED_COUNT_LABEL):
            continue
        for follower in lines[index + 1 : index + 1 + _DECLARED_COUNT_WINDOW]:
            value = follower.strip()
            if value.isdigit():
                return int(value)
        return None
    return None


def declared_count_from_pdf(pdf_file: Union[bytes, io.BytesIO, object]) -> Optional[int]:
    """Extract the PDF's declared damage item count, or None when not stated."""
    if isinstance(pdf_file, (bytes, bytearray)):
        pdf_file = io.BytesIO(pdf_file)
    return declared_count_from_lines(clean_lines(extract_pages(pdf_file)))


def precheck_paste(
    pdf_file: Union[bytes, io.BytesIO, object], table_text: str
) -> PastePrecheckReport:
    """Screen the pasted damage-table text against the PDF before a full check.

    `pdf_file` may be raw bytes or anything pdfplumber.open() accepts. A PDF
    that cannot be read is reported as a warning rather than raised, so the
    upload page always gets a report back; the full pipeline will surface the
    underlying error if the user proceeds anyway.
    """
    items, _ = parse_damage_table(table_text)
    complete_count = sum(1 for item in items if _is_complete_record(item))
    duplicates = duplicate_item_ids(items)
    header_rows = count_header_rows(table_text)
    missing_columns = missing_column_labels(table_text)

    declared: Optional[int] = None
    pdf_error: Optional[str] = None
    try:
        declared = declared_count_from_pdf(pdf_file)
    except Exception as error:  # noqa: BLE001 - any unreadable PDF becomes a warning
        logger.warning("Paste pre-check could not scan the PDF: %s", error)
        pdf_error = str(error) or error.__class__.__name__

    warnings = _build_warnings(
        declared, len(items), complete_count, duplicates, header_rows, pdf_error
    )
    notes = _build_notes(missing_columns)
    logger.info(
        "Paste pre-check: %d record(s) (%d complete) against declared count %s; "
        "%d warning(s), %d note(s)",
        len(items),
        complete_count,
        declared,
        len(warnings),
        len(notes),
    )
    return PastePrecheckReport(
        declared_count=declared,
        record_count=len(items),
        complete_count=complete_count,
        duplicate_ids=duplicates,
        header_row_count=header_rows,
        missing_columns=missing_columns,
        warnings=warnings,
        notes=notes,
    )


def _build_warnings(
    declared: Optional[int],
    record_count: int,
    complete_count: int,
    duplicates: list[str],
    header_rows: int,
    pdf_error: Optional[str],
) -> list[str]:
    """Turn the screening signals into user-facing warning sentences."""
    warnings: list[str] = []

    if record_count == 0:
        warnings.append(
            "No damage item records were found in the pasted text - the damage table "
            "looks empty or was not copied out of the web form as plain text."
        )
    else:
        if header_rows > 1:
            warnings.append(
                f"The pasted text contains {header_rows} table header rows, so more than "
                "one damage table (or the same table more than once) appears to have been pasted."
            )
        if duplicates:
            warnings.append(
                "Damage item ID(s) pasted more than once: "
                + ", ".join(duplicates)
                + ". The same table may have been pasted in twice."
            )
        incomplete = record_count - complete_count
        if incomplete:
            warnings.append(
                f"{incomplete} of {record_count} pasted record(s) are missing their trailing "
                "cost amounts, so the paste looks cut off part-way through a record."
            )
        if declared is not None:
            if complete_count < declared:
                warnings.append(
                    f"The PDF declares {declared} damage item(s) but the pasted text contains "
                    f"only {complete_count} complete record(s) - part of the table may not "
                    "have been copied."
                )
            elif complete_count > declared:
                warnings.append(
                    f"The pasted text contains {complete_count} complete record(s) but the PDF "
                    f"declares only {declared} damage item(s) - extra or duplicated rows may "
                    "have been pasted."
                )

    if pdf_error:
        warnings.append(
            f"The PDF could not be pre-scanned for its declared item count ({pdf_error}), "
            "so the record count comparison was skipped."
        )
    elif declared is None and record_count:
        warnings.append(
            "The PDF does not state how many damage items to expect, so the pasted record "
            "count could not be reconciled against it."
        )

    return warnings


def _build_notes(missing_columns: list[str]) -> list[str]:
    """Informational observations that never gate the submission.

    Copying the table body without its header row is normal, so absent column
    labels are worth mentioning but are not treated as a problem.
    """
    if not missing_columns:
        return []
    return [
        "Column label(s) not seen in the pasted text: "
        + ", ".join(missing_columns)
        + ". This is expected when the table was copied without its header row."
    ]
