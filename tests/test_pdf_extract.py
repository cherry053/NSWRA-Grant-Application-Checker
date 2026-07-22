"""Tests for the marker-based page skipping in core.pdf_extract.

Real (tiny) PDFs are built with reportlab - already a project dependency for
the feedback report - so extract_pages is exercised through pdfplumber
exactly as in production, not against mocked page objects.
"""

from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from core.pdf_extract import clean_lines, extract_pages
from core.section_splitter import split_sections

GARBLE_LINES = ["x9 zz DI-0 01 frag", "ment ed col umn s"]


def build_pdf(pages: list[list[str]]) -> BytesIO:
    """One PDF with the given lines drawn top-down on each page."""
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    for lines in pages:
        y = 800
        for line in lines:
            pdf.drawString(40, y, line)
            y -= 20
        pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer


def make_export(table_pages: int = 2) -> list[list[str]]:
    """A miniature SmartyGrants export: fields, table boundary pages,
    garbled table pages in between, then the post-table section."""
    return [
        ["1. Grant Program Information (EPAR)", "Organisation Name *", "Taree Council"],
        ["Damage Information", "The table below lists each damaged asset."],
        *[GARBLE_LINES for _ in range(table_pages)],
        ["Number of Damage Items", "Number of damaged items being restored *", "3"],
        ["6. Declaration and Authorisation", "I agree *"],
    ]


def flatten(pages: list[list[str]]) -> str:
    return "\n".join(line for page in pages for line in page)


def test_table_pages_are_skipped():
    pdf = build_pdf(make_export(table_pages=2))
    pages = extract_pages(pdf)
    text = flatten(pages)
    assert "Organisation Name *" in text
    assert "Number of damaged items being restored *" in text
    assert GARBLE_LINES[0] not in text
    # 6 pages in the document, the 2 garbled ones never extracted.
    assert len(pages) == 4


def test_on_page_reports_progress_and_skips_reads():
    calls: list[tuple[int, int]] = []
    pdf = build_pdf(make_export(table_pages=3))
    extract_pages(pdf, on_page=lambda done, total: calls.append((done, total)))
    totals = {total for _, total in calls}
    assert totals == {7}  # 2 top + 3 table + 2 bottom pages in the document
    assert [done for done, _ in calls] == list(range(1, len(calls) + 1))
    # Top section (2 pages) + bottom section (2 pages) read; table never read.
    assert len(calls) == 4


def test_missing_pre_marker_falls_back_to_every_page():
    export = make_export(table_pages=1)
    export[1] = ["Some other heading", "No table boundary on this page."]
    pdf = build_pdf(export)
    pages = extract_pages(pdf)
    assert len(pages) == 5
    assert GARBLE_LINES[0] in flatten(pages)


def test_missing_post_marker_still_keeps_all_content():
    export = make_export(table_pages=1)
    export[3] = ["An unexpected wording for the item count", "3"]
    pdf = build_pdf(export)
    pages = extract_pages(pdf)
    # Bottom-up read runs all the way back to the table, so nothing is lost.
    assert "6. Declaration and Authorisation" in flatten(pages)
    assert "An unexpected wording for the item count" in flatten(pages)


def test_mid_sentence_mention_does_not_end_top_section():
    export = make_export(table_pages=1)
    # A guidance sentence mentioning the heading mid-line must not match.
    export[0].append("Provide the damage information for every item below.")
    pdf = build_pdf(export)
    pages = extract_pages(pdf)
    # Page 1 did not trigger the marker: page 2's real heading did, and the
    # post-table content is still present.
    assert "Number of damaged items being restored *" in flatten(pages)
    assert len(pages) == 4


def test_extracted_pages_feed_the_section_splitter():
    pdf = build_pdf(make_export(table_pages=2))
    pre_lines, post_lines = split_sections(clean_lines(extract_pages(pdf)))
    assert "Organisation Name *" in pre_lines
    # The boundary pages' own residue is cut at the heading lines.
    assert "The table below lists each damaged asset." not in pre_lines
    assert post_lines[0].startswith("Number of Damage Items")
