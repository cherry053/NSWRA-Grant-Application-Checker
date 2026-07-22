DAMAGE_TABLE_START = "Damage Information"
DAMAGE_TABLE_END = "Number of Damage Items"


def split_sections(lines: list[str]) -> tuple[list[str], list[str]]:
    """Split cleaned PDF lines into the parts before and after the damage table.

    The damage table itself (between the 'Damage Information' heading and the
    'Number of Damage Items' heading) extracts as shredded column fragments,
    so it is discarded here; its data comes from the pasted text export instead.
    Missing anchors degrade gracefully: the affected boundary just isn't cut.
    """
    start = next((i for i, line in enumerate(lines) if line == DAMAGE_TABLE_START), len(lines))
    end = next((i for i, line in enumerate(lines) if line.startswith(DAMAGE_TABLE_END)), start)
    return lines[:start], lines[end:]
