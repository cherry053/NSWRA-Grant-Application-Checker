"""Tests for the upload-time screening of the pasted damage-table text.

The synthetic records below follow the plain-text web-form export shape that
core.damage_table_parser walks: an Asset Category anchor line, the identity
head, the location numbers, the option dumps with their Clear anchors, the
evidence upload blocks, and the trailing block of five cost amounts.
"""

from core.paste_precheck import (
    EXPECTED_COLUMN_LABELS,
    count_header_rows,
    declared_count_from_lines,
    duplicate_item_ids,
    missing_column_labels,
    precheck_paste,
)
from core.damage_table_parser import parse_damage_table

HEADER_ROW = "\t".join(EXPECTED_COLUMN_LABELS)


def make_record(item_id: str = "DI-001", complete: bool = True) -> str:
    """One damage item record in the plain-text export layout."""
    lines = [
        "Public Infrastructure",
        item_id,
        "A-100",
        "Smith Street Culvert",
        "01/03/2025",
        "10 Smith St, Taree NSW 2430, Australia",
        "5.2",
        "4.8",
        "6.1",
        "152.1",
        "-31.5",
        "152.2",
        "-31.6",
        "Road/s",
        "Clear selected value for Asset Sub-Category",
        "Culverts",
        "Local Road",
        "Two lanes",
        "Two-way",
        "200m x 7m",
        "Sealed",
        "Clear selected value for Asset Material",
        "Yes",
        "No",
        "Clear selected value for pre-disaster function",
        "Filename",
        f"{item_id}_PredisasterEvidence.jpg",
        "File size",
        "2.1 MB",
        "Filename",
        f"{item_id}_DamageEvidence.jpg",
        "File size",
        "3.4 MB",
        "Culvert washed away by flood water.",
        "Quantity surveyor cost estimate.",
    ]
    if complete:
        lines.extend(["$100.00", "$20.00", "$10.00", "$5.00", "$135.00"])
    return "\n".join(lines)


def make_paste(*records: str, header: bool = True) -> str:
    parts = [HEADER_ROW] if header else []
    parts.extend(records)
    return "\n".join(parts)


def make_pdf_lines(declared: int) -> list[str]:
    return [
        "5. EPAR Funding Request",
        "Number of damaged items being restored *",
        "Response required.",
        str(declared),
        "Total Amount Requested",
    ]


class FailingPdf:
    """Stand-in for a PDF that pdfplumber cannot open."""

    def read(self, *args: object) -> bytes:
        raise OSError("not a PDF")

    def seek(self, *args: object) -> int:
        return 0


def test_synthetic_record_parses_as_complete():
    items, _ = parse_damage_table(make_record("DI-001"))
    assert len(items) == 1
    assert items[0].damage_item_id == "DI-001"
    assert items[0].cost_total is not None


def test_truncated_record_is_not_complete():
    items, _ = parse_damage_table(make_record("DI-001", complete=False))
    assert len(items) == 1
    assert items[0].cost_total is None


def test_declared_count_from_lines_skips_guidance():
    assert declared_count_from_lines(make_pdf_lines(3)) == 3


def test_declared_count_missing_label_returns_none():
    assert declared_count_from_lines(["Total Amount Requested", "$1.00"]) is None


def test_duplicate_item_ids_first_seen_order():
    items, _ = parse_damage_table(
        make_paste(make_record("DI-001"), make_record("DI-002"), make_record("DI-001"))
    )
    assert duplicate_item_ids(items) == ["DI-001"]


def test_count_header_rows_detects_doubled_paste():
    single = make_paste(make_record("DI-001"))
    assert count_header_rows(single) == 1
    assert count_header_rows(single + "\n" + single) == 2


def test_missing_column_labels_flags_headerless_paste():
    missing = missing_column_labels(make_record("DI-001"))
    assert "Asset Category" in missing
    assert "Damage Item ID" in missing
    # These two labels still appear in the record's Clear anchor lines.
    assert "Asset Sub-Category" not in missing
    assert "Asset Material" not in missing


def test_missing_column_labels_accepts_full_header():
    assert missing_column_labels(make_paste(make_record("DI-001"))) == []


def test_headerless_paste_is_noted_but_never_warned(monkeypatch):
    monkeypatch.setattr(
        "core.paste_precheck.declared_count_from_pdf", lambda pdf: 1
    )
    report = precheck_paste(b"unused", make_record("DI-001"))
    assert report.missing_columns  # the check still runs and records its finding
    assert not report.has_warnings  # but it never gates the submission
    assert any("header row" in note for note in report.notes)


def test_empty_paste_warns(monkeypatch):
    monkeypatch.setattr(
        "core.paste_precheck.declared_count_from_pdf", lambda pdf: 2
    )
    report = precheck_paste(b"unused", "")
    assert report.record_count == 0
    assert any("empty" in warning for warning in report.warnings)


def test_clean_paste_raises_no_warnings(monkeypatch):
    monkeypatch.setattr(
        "core.paste_precheck.declared_count_from_pdf", lambda pdf: 2
    )
    report = precheck_paste(
        b"unused", make_paste(make_record("DI-001"), make_record("DI-002"))
    )
    assert report.record_count == 2
    assert report.complete_count == 2
    assert report.declared_count == 2
    assert not report.has_warnings


def test_partial_paste_warns_about_declared_count(monkeypatch):
    monkeypatch.setattr(
        "core.paste_precheck.declared_count_from_pdf", lambda pdf: 3
    )
    report = precheck_paste(b"unused", make_paste(make_record("DI-001")))
    assert report.complete_count == 1
    assert any("declares 3" in warning for warning in report.warnings)


def test_truncated_final_record_warns(monkeypatch):
    monkeypatch.setattr(
        "core.paste_precheck.declared_count_from_pdf", lambda pdf: 2
    )
    report = precheck_paste(
        b"unused",
        make_paste(make_record("DI-001"), make_record("DI-002", complete=False)),
    )
    assert report.record_count == 2
    assert report.complete_count == 1
    assert any("cut off" in warning for warning in report.warnings)


def test_doubled_paste_warns_on_duplicates_and_headers(monkeypatch):
    monkeypatch.setattr(
        "core.paste_precheck.declared_count_from_pdf", lambda pdf: 1
    )
    single = make_paste(make_record("DI-001"))
    report = precheck_paste(b"unused", single + "\n" + single)
    assert report.header_row_count == 2
    assert report.duplicate_ids == ["DI-001"]
    assert any("header rows" in warning for warning in report.warnings)
    assert any("more than once" in warning for warning in report.warnings)
    assert any("declares only 1" in warning for warning in report.warnings)


def test_unreadable_pdf_becomes_warning_not_error():
    report = precheck_paste(FailingPdf(), make_paste(make_record("DI-001")))
    assert report.declared_count is None
    assert any("could not be pre-scanned" in warning for warning in report.warnings)
