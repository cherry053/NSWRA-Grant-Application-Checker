from typing import Callable, Optional

import pdfplumber

from core.section_splitter import DAMAGE_TABLE_END, DAMAGE_TABLE_START

# Markers bounding the garbled Damage Information table, whose pages we skip.
# The wording is shared with core.section_splitter so the page-skip and the
# line-level cut can never drift apart. Matching is case-insensitive and
# accepts any listed wording, because a missed marker forces extraction of
# every table page (minutes, not seconds).
PRE_TABLE_MARKERS = (DAMAGE_TABLE_START.lower(),)
POST_TABLE_MARKERS = (
    DAMAGE_TABLE_END.lower(),
    "number of damaged items being restored",
)

# Reports (pages_extracted_so_far, total_pages) after each page is read, so a
# progress bar can advance while the parser works through the document.
PageProgressCallback = Callable[[int, int], None]

# Lines appearing near the top of at least this share of pages are treated as
# repeated page headers and removed everywhere.
_HEADER_PAGE_SHARE = 0.5
_HEADER_SCAN_DEPTH = 4


def _has_marker_line(text: str | None, markers: tuple[str, ...]) -> bool:
    """True when any line of the page starts with one of the markers.

    Anchoring the match to the start of a line (rather than searching the
    whole page text) keeps a guidance sentence that merely mentions
    'damage information' mid-sentence from ending the top section early -
    which would silently skip every page up to the damage table.
    """
    if not text:
        return False
    for raw_line in text.split("\n"):
        line = raw_line.strip().lower()
        if any(line.startswith(marker) for marker in markers):
            return True
    return False


def _page_lines(text: str | None) -> list[str]:
    return [line.strip() for line in text.split("\n")] if text else []


def extract_pages(file, on_page: Optional[PageProgressCallback] = None) -> list[list[str]]:
    """Extract a SmartyGrants PDF as stripped lines per page, skipping the
    garbled Damage Information table.

    `file` is anything pdfplumber.open() accepts (path, bytes, or a
    file-like object such as Streamlit's UploadedFile).

    Extracts text top-down only until the page containing a PRE_TABLE_MARKERS
    heading, then bottom-up only until the page containing a
    POST_TABLE_MARKERS heading - the table pages in between are never read,
    which is where the time goes. Falls back to every page if a marker is
    missing. `on_page`, when given, is called as `on_page(pages_read, total)`
    after each page so the caller can show live progress.
    """
    with pdfplumber.open(file) as pdf:
        pages = pdf.pages
        total = len(pages)
        pages_read = 0

        def _read(index: int) -> str | None:
            nonlocal pages_read
            text = pages[index].extract_text()
            pages_read += 1
            if on_page is not None:
                on_page(pages_read, total)
            return text

        # Read top-down, extracting text only as far as the pre-table marker.
        top_texts: list[str | None] = []
        top_end: Optional[int] = None
        for i in range(total):
            text = _read(i)
            top_texts.append(text)
            if _has_marker_line(text, PRE_TABLE_MARKERS):
                top_end = i
                break

        # Pre-table marker missing: top_texts already holds every page.
        if top_end is None:
            return [_page_lines(text) for text in top_texts]

        # Read bottom-up, extracting only as far as the post-table marker and
        # never past the top section we already have.
        bottom_texts: list[str | None] = []
        for i in range(total - 1, top_end, -1):
            text = _read(i)
            bottom_texts.append(text)
            if _has_marker_line(text, POST_TABLE_MARKERS):
                break
        bottom_texts.reverse()

    # When the post-table marker is missing the bottom loop simply read every
    # page after the top section, so no real content is dropped either way.
    return [_page_lines(text) for text in top_texts + bottom_texts]


def _is_page_footer(line: str) -> bool:
    """Match footers of the form 'Page 3 of 21' without regex."""
    tokens = line.split()
    return (
        len(tokens) == 4
        and tokens[0] == "Page"
        and tokens[2] == "of"
        and tokens[1].isdigit()
        and tokens[3].isdigit()
    )


def _repeated_header_lines(pages: list[list[str]]) -> set[str]:
    """Lines that recur at the top of most pages (title, application number, etc.)."""
    counts: dict[str, int] = {}
    for page in pages:
        for line in set(page[:_HEADER_SCAN_DEPTH]):
            if line:
                counts[line] = counts.get(line, 0) + 1
    threshold = max(2, int(len(pages) * _HEADER_PAGE_SHARE))
    return {line for line, count in counts.items() if count >= threshold}


def clean_lines(pages: list[list[str]]) -> list[str]:
    """Flatten pages into one line list with repeated headers and page footers removed."""
    headers = _repeated_header_lines(pages)
    lines: list[str] = []
    for page in pages:
        for position, line in enumerate(page):
            if position < _HEADER_SCAN_DEPTH and line in headers:
                continue
            if _is_page_footer(line):
                continue
            lines.append(line)
    return lines
