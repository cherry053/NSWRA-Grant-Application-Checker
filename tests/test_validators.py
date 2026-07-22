"""Tests for the export-limitation disclaimers and their effect on the checks.

Selections the text export cannot show (Asset Material, the pre-disaster
function answer) must never fail the check result: they surface as
informational notices asking the user to double-check, while the
"Damage Table Parsed Cleanly" criterion only reacts to genuine parse problems.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_paste_precheck import make_record

from core.damage_table_parser import parse_damage_table
from core.models import ApplicationData
from core.validators import run_checks, selection_notices


def _criterion(result, name):
    matches = [c for c in result.criteria if c.name == name]
    assert len(matches) == 1, f"expected exactly one '{name}' criterion"
    return matches[0]


def test_export_limitations_are_notes_not_warnings():
    items, warnings = parse_damage_table(make_record("DI-001"))
    assert not warnings  # a complete record raises no genuine parse problems
    assert len(items[0].parse_notes) == 2  # material + pre-disaster function


def test_notes_do_not_fail_parsed_cleanly_criterion():
    items, warnings = parse_damage_table(make_record("DI-001"))
    result = run_checks(ApplicationData(), items, warnings)
    assert _criterion(result, "Damage Table Parsed Cleanly").passed


def test_truncated_record_still_fails_parsed_cleanly_criterion():
    items, warnings = parse_damage_table(make_record("DI-001", complete=False))
    result = run_checks(ApplicationData(), items, warnings)
    assert any("cost amounts" in warning for warning in warnings)
    assert not _criterion(result, "Damage Table Parsed Cleanly").passed


def test_notices_group_affected_items_and_ask_for_a_double_check():
    items, _ = parse_damage_table(make_record("DI-001") + "\n" + make_record("DI-002"))
    notices = selection_notices(items)
    assert len(notices) == 2  # one per limitation, not one per item
    assert all("double-check" in notice for notice in notices)
    assert all("DI-001, DI-002" in notice for notice in notices)


def test_notices_never_lower_the_confidence_score():
    items, warnings = parse_damage_table(make_record("DI-001"))
    with_notes = run_checks(ApplicationData(), items, warnings)
    for item in items:
        item.parse_notes.clear()
    without_notes = run_checks(ApplicationData(), items, warnings)
    assert with_notes.confidence_score == without_notes.confidence_score
    assert with_notes.overall_status == without_notes.overall_status
