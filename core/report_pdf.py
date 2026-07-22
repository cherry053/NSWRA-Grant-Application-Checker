"""Render a CheckResult as a downloadable PDF feedback report."""

from decimal import Decimal
from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.models import CheckResult, CriterionResult
from core.sections import group_by_section, section_passed_counts

NSW_NAVY = colors.HexColor("#002664")
ROW_SHADE = colors.HexColor("#F4F4F7")

PASS_HEX = "#00AA45"
REVIEW_HEX = "#C4780A"
FAIL_HEX = "#D7153A"

PAGE_MARGIN = 18 * mm


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("ReportTitle", parent=base["Title"], textColor=NSW_NAVY, spaceAfter=2),
        "meta": ParagraphStyle("Meta", parent=base["Normal"], fontSize=9, textColor=colors.HexColor("#555555")),
        "section": ParagraphStyle(
            "SectionHeading", parent=base["Heading2"], textColor=NSW_NAVY, spaceBefore=10, spaceAfter=4
        ),
        "cell": ParagraphStyle("Cell", parent=base["Normal"], fontSize=8.5, leading=11),
        "header_cell": ParagraphStyle(
            "HeaderCell",
            parent=base["Normal"],
            fontSize=8.5,
            leading=11,
            textColor=colors.white,
            fontName="Helvetica-Bold",
        ),
        "badge": ParagraphStyle(
            "Badge", parent=base["Normal"], fontSize=8.5, leading=11, alignment=1, fontName="Helvetica-Bold"
        ),
    }


def _badge_text(criterion: CriterionResult) -> tuple[str, str]:
    if criterion.passed:
        return "PASS", PASS_HEX
    if criterion.severity == "warning":
        return "REVIEW", REVIEW_HEX
    return "FAIL", FAIL_HEX


def _paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text), style)


def _badge_paragraph(criterion: CriterionResult, style: ParagraphStyle) -> Paragraph:
    badge, colour = _badge_text(criterion)
    return Paragraph(f'<font color="{colour}">{badge}</font>', style)


def _summary_table(result: CheckResult, styles: dict[str, ParagraphStyle]) -> Table:
    passed = sum(1 for criterion in result.criteria if criterion.passed)
    total = len(result.criteria)
    items_total = sum(
        (item.cost_total for item in result.damage_items if item.cost_total is not None), Decimal("0")
    )
    erc = result.total_requested if result.total_requested is not None else items_total

    rows = [
        ["Overall status", result.overall_status],
        ["Confidence score", f"{result.confidence_score}%"],
        ["Criteria passed", f"{passed} / {total}"],
        ["Flags raised", str(total - passed)],
        ["Total ERC", f"${erc:,.2f}"],
        ["Damage items parsed", str(len(result.damage_items))],
    ]
    table = Table(
        [[_paragraph(label, styles["cell"]), _paragraph(value, styles["cell"])] for label, value in rows],
        colWidths=[45 * mm, 60 * mm],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), ROW_SHADE),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _criteria_table(criteria: list[CriterionResult], styles: dict[str, ParagraphStyle]) -> Table:
    rows = [
        [
            _paragraph("Criterion", styles["header_cell"]),
            _paragraph("Result", styles["header_cell"]),
            _paragraph("Detail", styles["header_cell"]),
        ]
    ]
    for criterion in criteria:
        rows.append(
            [
                _paragraph(criterion.name, styles["cell"]),
                _badge_paragraph(criterion, styles["badge"]),
                _paragraph(criterion.detail, styles["cell"]),
            ]
        )

    table = Table(rows, colWidths=[52 * mm, 18 * mm, 104 * mm], repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NSW_NAVY),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_SHADE]),
            ]
        )
    )
    return table


def _damage_items_table(result: CheckResult, styles: dict[str, ParagraphStyle]) -> Table:
    rows = [
        [
            _paragraph("Damage ID", styles["header_cell"]),
            _paragraph("Asset", styles["header_cell"]),
            _paragraph("Accessible", styles["header_cell"]),
            _paragraph("Total estimate", styles["header_cell"]),
        ]
    ]
    for item in result.damage_items:
        total = f"${item.cost_total:,.2f}" if item.cost_total is not None else "-"
        rows.append(
            [
                _paragraph(item.damage_item_id or "-", styles["cell"]),
                _paragraph(item.asset_name or "-", styles["cell"]),
                _paragraph(item.date_accessible or "-", styles["cell"]),
                _paragraph(total, styles["cell"]),
            ]
        )
    table = Table(rows, colWidths=[24 * mm, 80 * mm, 28 * mm, 42 * mm], repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NSW_NAVY),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_SHADE]),
            ]
        )
    )
    return table


def build_feedback_pdf(result: CheckResult) -> bytes:
    """Build the feedback report PDF and return it as bytes for download."""
    styles = _styles()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=PAGE_MARGIN,
        rightMargin=PAGE_MARGIN,
        topMargin=PAGE_MARGIN,
        bottomMargin=PAGE_MARGIN,
        title="Grant Application Quality Report",
    )

    story = [
        _paragraph("Grant Application Quality Report", styles["title"]),
        _paragraph(
            f"{result.application_id or 'Unknown application'} - {result.applicant_name or 'Unknown applicant'}"
            f"  |  Scanned on {result.scanned_at or 'unknown date'}",
            styles["meta"],
        ),
        Spacer(1, 6 * mm),
        _summary_table(result, styles),
        Spacer(1, 4 * mm),
    ]

    if result.notices:
        story.append(_paragraph("Please double-check", styles["section"]))
        for notice in result.notices:
            story.append(_paragraph(notice, styles["cell"]))
            story.append(Spacer(1, 1.5 * mm))

    for section, criteria in group_by_section(result.criteria).items():
        passed, total = section_passed_counts(criteria)
        story.append(_paragraph(f"{section}  ({passed}/{total} passed)", styles["section"]))
        story.append(_criteria_table(criteria, styles))

    if result.damage_items:
        story.append(_paragraph("Damage Items Summary", styles["section"]))
        story.append(_damage_items_table(result, styles))

    document.build(story)
    return buffer.getvalue()
