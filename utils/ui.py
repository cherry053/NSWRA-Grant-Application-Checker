"""Streamlit rendering helpers: NSW-branded page chrome and HTML fragments.

All HTML lives in static/html templates; all styling lives in static/css and
the locally vendored NSW Design System stylesheet (no CDN dependency, so the
branding still renders inside firewalled government networks).
"""

from functools import lru_cache
from html import escape
from pathlib import Path

import streamlit as st

from core.filters import criterion_status
from core.models import CriterionResult

STATIC_DIR = Path(__file__).parent.parent / "static"

# Served by Streamlit's static file route (server.enableStaticServing).
NSW_DESIGN_SYSTEM_CSS = (
    '<link rel="stylesheet" href="/app/static/vendor/nsw-design-system-3.24.10.css">'
)

# NSW Design System palette. Every text/background pairing used below meets
# WCAG AA contrast (white on the status colours, dark text on the tints).
NSW_TEXT_DARK = "#22272B"
NSW_SUCCESS = "#008A07"
NSW_SUCCESS_DARK = "#00490B"  # border ring on the pass icon
NSW_WARNING = "#C95000"
NSW_ERROR = "#B81237"
WHITE = "#FFFFFF"

# overall check status -> (label, colour) for the readiness badge.
_READINESS_STYLES = {
    "PASS": ("Ready", NSW_SUCCESS),
    "FAIL": ("Needs review", NSW_ERROR),
    "PARTIAL": ("Partial", NSW_WARNING),
}

# Inline SVG status icons for the criteria rows, drawn in the NSW status
# palette. The row's PASS/REVIEW/FAIL badge carries the same meaning as text,
# so colour is never the only cue (WCAG 1.4.1).
_ICON_PASS = (
    '<svg viewBox="0 0 24 24" width="22" height="22" focusable="false">'
    f'<circle cx="12" cy="12" r="10" fill="{NSW_SUCCESS}" stroke="{NSW_SUCCESS_DARK}" stroke-width="2"/>'
    f'<path d="M10 15.2 6.8 12l-1.4 1.4L10 18l8.6-8.6L17.2 8z" fill="{WHITE}"/>'
    "</svg>"
)
_ICON_REVIEW = (
    '<svg viewBox="0 0 24 24" width="22" height="22" focusable="false">'
    f'<path d="M12 2.5 22.6 20.5H1.4z" fill="{NSW_WARNING}"/>'
    f'<path d="M11 9.5h2v6h-2zm0 7.5h2v2h-2z" fill="{WHITE}"/>'
    "</svg>"
)
_ICON_FAIL = (
    '<svg viewBox="0 0 24 24" width="22" height="22" focusable="false">'
    f'<circle cx="12" cy="12" r="10" fill="{NSW_ERROR}"/>'
    f'<path d="M16.9 8.5 15.5 7.1 12 10.6 8.5 7.1 7.1 8.5l3.5 3.5-3.5 3.5 1.4 1.4 '
    f'3.5-3.5 3.5 3.5 1.4-1.4-3.5-3.5z" fill="{WHITE}"/>'
    "</svg>"
)

_CRITERIA_ICONS = {
    "Pass": _ICON_PASS,
    "Review": _ICON_REVIEW,
    "Fail": _ICON_FAIL,
}

@lru_cache(maxsize=None)
def _load(*relative_path: str) -> str:
    """Read a static template once per process; templates never change at runtime."""
    return (STATIC_DIR / Path(*relative_path)).read_text()


def render_masthead() -> None:
    st.markdown(_load("html", "masthead.html"), unsafe_allow_html=True)


def render_nosection() -> None:
    st.markdown(_load("html", "nosection.html"), unsafe_allow_html=True)


def render_splash() -> None:
    """Branded loading splash, shown once per session on first page load.

    Pure CSS: the overlay fades out on its own, so it costs no reruns and no
    artificial delay. Re-runs skip it entirely.
    """
    if st.session_state.get("_splash_shown"):
        return
    st.session_state["_splash_shown"] = True
    st.markdown(_load("html", "splash.html"), unsafe_allow_html=True)


def render_header(title: str) -> None:
    """Inject the stylesheets and render the NSW masthead, header, and title bar."""
    st.markdown(NSW_DESIGN_SYSTEM_CSS, unsafe_allow_html=True)
    st.markdown(f"<style>{_load('css', 'main.css')}</style>", unsafe_allow_html=True)
    render_masthead()
    st.markdown(_load("html", "header.html"), unsafe_allow_html=True)
    st.markdown(
        f'<div class="header-bar" id="main-content"><h1 class="header-title">{escape(title)}</h1></div>',
        unsafe_allow_html=True,
    )


def render_cards() -> None:
    st.markdown(_load("html", "cards.html"), unsafe_allow_html=True)


def render_errormessage() -> None:
    st.markdown(_load("html", "errormessage.html"), unsafe_allow_html=True)


def render_footer() -> None:
    st.markdown(_load("html", "footer.html"), unsafe_allow_html=True)


def render_uploadinfo() -> None:
    st.markdown(_load("html", "uploadinfo.html"), unsafe_allow_html=True)


def render_readiness_badge(status: str) -> None:
    label, colour = _READINESS_STYLES.get(status, ("Unknown", NSW_TEXT_DARK))
    html = _load("html", "readiness_badge.html").format(label=escape(label), colour=colour)
    st.markdown(html, unsafe_allow_html=True)


def render_criteria_rows(criterion: CriterionResult) -> None:
    """Render one criterion as a coloured row: status icon, name, and badge."""
    status = criterion_status(criterion)
    html = _load("html", "criteria_rows.html").format(
        level=status.lower(),
        icon=_CRITERIA_ICONS[status],
        name=escape(criterion.name),
        badge=status.upper(),
    )
    st.markdown(html, unsafe_allow_html=True)


def render_empty_state(title: str, message: str) -> None:
    html = _load("html", "empty_state.html").format(title=escape(title), message=escape(message))
    st.markdown(html, unsafe_allow_html=True)


def _short_section(section: str) -> str:
    """'4. Damage Information' -> 'Damage Information' for a compact card tag."""
    label = section.strip()
    if label and label[0].isdigit() and "." in label:
        label = label.split(".", 1)[1].strip()
    return label or "General"


def render_flag_card(criterion: CriterionResult) -> None:
    """Render one raised flag as an NSW-styled severity card.

    Layout follows the results wireframe: a severity badge and a category tag
    on the head, then the explanatory detail beneath.
    """
    if criterion.severity == "warning":
        level, badge = "review", "REVIEW"
    else:
        level, badge = "fail", "FAIL"

    html = _load("html", "flag_card.html").format(
        level=level,
        badge=badge,
        category=escape(_short_section(criterion.section)),
        name=escape(criterion.name),
        detail=escape(criterion.detail),
    )
    st.markdown(html, unsafe_allow_html=True)


def render_notice_card(notice: str) -> None:
    """Render one informational disclaimer as an INFO card.

    Notices flag selections the text export cannot show (e.g. Asset Material)
    so the user knows to double-check them manually; they never count against
    the check result.
    """
    html = _load("html", "flag_card.html").format(
        level="info",
        badge="INFO",
        category="Please double-check",
        name="Selection not visible to the checker",
        detail=escape(notice),
    )
    st.markdown(html, unsafe_allow_html=True)


def render_flags(criteria: list[CriterionResult], notices: list[str] | None = None) -> None:
    """Render raised flags as cards (most severe first), then any disclaimers.

    When nothing failed, a success note still precedes the disclaimer cards so
    the panel reads as "all clear, but double-check these" rather than empty.
    """
    notices = notices or []
    flagged = [c for c in criteria if not c.passed]
    if not flagged:
        st.markdown(
            '<div class="flags-empty">'
            '<span class="flags-empty__icon" aria-hidden="true">&#10003;</span>'
            "<span>No flags raised. All checked criteria passed.</span></div>",
            unsafe_allow_html=True,
        )
    flagged.sort(key=lambda c: 0 if c.severity == "critical" else 1)
    for criterion in flagged:
        render_flag_card(criterion)
    for notice in notices:
        render_notice_card(notice)
