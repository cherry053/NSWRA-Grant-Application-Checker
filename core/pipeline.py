import io
import logging
from datetime import datetime
from typing import Callable, Optional, Union

from core.damage_table_parser import parse_damage_table
from core.field_parser import parse_application_header, parse_post_table_fields, parse_pre_table_fields
from core.models import ApplicationData, CheckResult
from core.pdf_extract import clean_lines, extract_pages
from core.section_splitter import split_sections
from core.validators import run_checks

logger = logging.getLogger(__name__)

# One user-facing message per pipeline stage, reported through `on_progress`
# so the interface can show what the checker is doing instead of freezing.
# Called as on_progress(step, total, message, stage_fraction) where
# `stage_fraction` (0.0-1.0) is how far through the current stage the work is:
# the document-reading stage reports it per extracted page, so the progress
# bar moves while the parser works instead of sitting still.
ProgressCallback = Callable[[int, int, str, float], None]

_STAGES = (
    "Reading document...",
    "Parsing application fields...",
    "Extracting damage table...",
    "Validating criteria...",
    "Generating report...",
)
TOTAL_STAGES = len(_STAGES)


def check_application(
    pdf_file: Union[bytes, io.BytesIO, object],
    damage_table_text: str,
    on_progress: Optional[ProgressCallback] = None,
) -> CheckResult:
    """Run a SmartyGrants PDF export plus its pasted damage-table text through all checks.

    The PDF is parsed up to the damage table and again after it; the table
    itself (which does not survive PDF text extraction) is read from
    `damage_table_text`, the table copied out of the web form as plain text.

    `pdf_file` may be raw bytes or anything pdfplumber.open() accepts (a path
    or a file-like object). `on_progress`, when given, is called as
    `on_progress(step, total, message, stage_fraction)` before each stage -
    and once per extracted page during the reading stage - so the caller can
    surface live progress to the user.
    """
    if isinstance(pdf_file, (bytes, bytearray)):
        pdf_file = io.BytesIO(pdf_file)

    def report(step: int) -> None:
        message = _STAGES[step]
        logger.info("check_application stage %d/%d: %s", step + 1, TOTAL_STAGES, message)
        if on_progress is not None:
            on_progress(step, TOTAL_STAGES, message, 0.0)

    def report_page(pages_read: int, page_total: int) -> None:
        # Advance the bar within the reading stage as each page is extracted.
        if on_progress is not None and page_total:
            on_progress(
                0,
                TOTAL_STAGES,
                f"Reading document... (page {pages_read} of {page_total})",
                pages_read / page_total,
            )

    report(0)
    pages = extract_pages(pdf_file, on_page=report_page)
    logger.info("Extracted %d page(s) from the PDF export", len(pages))

    report(1)
    meta = parse_application_header(pages)
    pre_lines, post_lines = split_sections(clean_lines(pages))
    data = ApplicationData()
    parse_pre_table_fields(pre_lines, data)
    parse_post_table_fields(post_lines, data)

    report(2)
    items, table_warnings = parse_damage_table(damage_table_text)
    logger.info("Parsed %d damage item(s), %d table warning(s)", len(items), len(table_warnings))

    report(3)
    result = run_checks(data, items, table_warnings)

    report(4)
    result.application_id = meta.get("application_id")
    result.applicant_name = data.organisation_name or meta.get("applicant_name")
    result.scanned_at = datetime.now().strftime("%d %b %Y, %I:%M %p")
    result.total_requested = data.total_amount_requested
    logger.info(
        "Check finished for %s: %s (confidence %d%%)",
        result.application_id or "unknown application",
        result.overall_status,
        result.confidence_score,
    )
    return result
