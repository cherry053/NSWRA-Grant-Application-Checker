import streamlit as st

st.set_page_config(page_title="Results | Grant Application Quality Checker", layout="wide")
st.page_link("app.py", label="Back to Grant Application Quality Checker", icon=":material/arrow_back:")


from core.filters import (
    VALID_STATUSES,
    filter_criteria,
    section_status,
    status_counts,
)
from core.models import CheckResult
from core.report_pdf import build_feedback_pdf
from core.sections import group_by_section, section_passed_counts
from utils.ui import (
    render_criteria_rows,
    render_empty_state,
    render_flags,
    render_footer,
    render_header,
    render_readiness_badge,
)

render_header("Grant Application Quality Checker")

# --- Session state ----------------------------------------------------------
#
# Filter values live in their own session keys (FILTER_*), separate from the
# widget keys. Streamlit discards widget-bound state whenever the widget is
# not rendered - i.e. every time the user visits the upload page - so binding
# the widgets directly to the stored values silently reset the filters on
# navigation. Each run re-seeds the widget keys from the stored values and the
# widgets sync back through on_change callbacks.

FILTER_STATUS = "filter_status"
FILTER_SEARCH = "filter_search"
_STATUS_WIDGET = "filter_status_widget"
_SEARCH_WIDGET = "filter_search_widget"

st.session_state.setdefault(FILTER_STATUS, list(VALID_STATUSES))
st.session_state.setdefault(FILTER_SEARCH, "")
st.session_state[_STATUS_WIDGET] = st.session_state[FILTER_STATUS]
st.session_state[_SEARCH_WIDGET] = st.session_state[FILTER_SEARCH]

# Coloured section icons (Streamlit colour directives), so a section's worst
# status is visible before the expander is opened.
SECTION_ICONS = {
    "Pass": ":green[:material/check_circle:]",
    "Review": ":orange[:material/warning:]",
    "Fail": ":red[:material/cancel:]",
}


def sync_status_filter() -> None:
    st.session_state[FILTER_STATUS] = st.session_state[_STATUS_WIDGET]


def sync_search_filter() -> None:
    st.session_state[FILTER_SEARCH] = st.session_state[_SEARCH_WIDGET]


def clear_search_filter() -> None:
    st.session_state[FILTER_SEARCH] = ""


def clear_all_filters() -> None:
    st.session_state[FILTER_STATUS] = list(VALID_STATUSES)
    st.session_state[FILTER_SEARCH] = ""


def _report_pdf_bytes(check: CheckResult) -> bytes:
    """Build the feedback PDF once per application and cache it for reruns."""
    cache: dict = st.session_state.setdefault("_report_pdf_cache", {})
    key = (check.application_id, check.scanned_at)
    if key not in cache:
        if len(cache) >= 8:  # keep the session cache small
            cache.clear()
        with st.spinner("Generating PDF report..."):
            cache[key] = build_feedback_pdf(check)
    return cache[key]


result: CheckResult | None = st.session_state.get("check_result")

title_col, new_col = st.columns([4, 1.3], vertical_alignment="center")

with title_col:
    st.header("Check results", anchor=False)

with new_col:
    if st.button("Check another application", type="primary", use_container_width=True):
        st.switch_page("app.py")

if result is None:
    render_empty_state(
        "No application checked yet",
        "Upload a SmartyGrants export on the home page to see its quality check results here.",
    )
    st.page_link("app.py", label="Back to upload", icon=":material/arrow_back:")
    st.stop()

passed_count = sum(1 for c in result.criteria if c.passed)
total_count = len(result.criteria)
flags_raised = total_count - passed_count

items_total = sum(item.cost_total for item in result.damage_items if item.cost_total is not None)
estimated_cost = result.total_requested if result.total_requested is not None else items_total

col_left, col_right = st.columns([3, 1])

with col_left:
    st.caption("APPLICATION")
    st.subheader(
        f"{result.application_id or 'Unknown ID'} - {result.applicant_name or 'Unknown applicant'}",
        anchor=False,
    )
    st.caption(f"Scanned on {result.scanned_at}")
    st.caption(f"{len(result.damage_items)} damaged item(s) parsed")

with col_right:
    render_readiness_badge(result.overall_status)
    st.download_button(
        "Download feedback (PDF)",
        data=_report_pdf_bytes(result),
        file_name=f"{result.application_id or 'application'}_feedback.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

st.divider()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Criteria passed", f"{passed_count} / {total_count}")

with col2:
    st.metric("Flags raised", flags_raised)

with col3:
    st.metric("Total ERC", f"${estimated_cost:,.0f}")

with col4:
    st.metric("Damage items", len(result.damage_items))

st.divider()

# --- Criteria filters --------------------------------------------------------

counts = status_counts(result.criteria)
search_active = bool(st.session_state[FILTER_SEARCH].strip())
filters_active = search_active or set(st.session_state[FILTER_STATUS]) != set(VALID_STATUSES)

with st.container(key="filter_panel"):
    st.markdown('<p class="filter-panel__heading">Filter criteria</p>', unsafe_allow_html=True)

    status_col, search_col, actions_col = st.columns([2, 2, 1], vertical_alignment="bottom")

    with status_col:
        st.multiselect(
            "Criterion status",
            options=list(VALID_STATUSES),
            key=_STATUS_WIDGET,
            on_change=sync_status_filter,
            format_func=lambda status: f"{status} ({counts[status]})",
            placeholder="All statuses",
            help="Keep only the statuses you want to see - e.g. select Pass to "
            "highlight everything this application passed.",
        )

    with search_col:
        st.text_input(
            "Search criteria",
            key=_SEARCH_WIDGET,
            on_change=sync_search_filter,
            placeholder="Criterion name, section or detail",
            help="Matches anywhere in the criterion name, its form section, or its "
            "detail text; press Enter to apply.",
        )

    with actions_col:
        st.button(
            "Clear search",
            use_container_width=True,
            on_click=clear_search_filter,
            disabled=not search_active,
        )
        st.button(
            "Clear all filters",
            use_container_width=True,
            on_click=clear_all_filters,
            disabled=not filters_active,
        )

    visible = filter_criteria(
        result.criteria, set(st.session_state[FILTER_STATUS]), st.session_state[FILTER_SEARCH]
    )

    st.markdown(
        f'<p class="filter-panel__count" role="status">Showing <strong>{len(visible)}</strong> '
        f"of {total_count} criteria</p>",
        unsafe_allow_html=True,
    )

if not visible:
    render_empty_state(
        "No criteria match the current filters",
        "Adjust the search term or status selection, or clear the filters to see every "
        "checked criterion.",
    )
    st.button("Clear all filters", key="clear_filters_empty", type="primary", on_click=clear_all_filters)

col1, col2 = st.columns(2)

with col1:
    st.header("Criteria summary", anchor=False)
    visible_sections = group_by_section(visible)
    for section, section_criteria in group_by_section(result.criteria).items():
        matching = visible_sections.get(section, [])
        if not matching:
            continue
        section_passed, section_total = section_passed_counts(section_criteria)
        icon = SECTION_ICONS[section_status(section_criteria)]
        label = f"{icon} {section} — {section_passed}/{section_total} passed"
        # Expand automatically while filtering so the matching criteria are
        # visible without another click.
        with st.expander(label, expanded=filters_active):
            if len(matching) != len(section_criteria):
                st.caption(f"Showing {len(matching)} of {len(section_criteria)} criteria in this section.")
            for criterion in matching:
                render_criteria_rows(criterion)
                if not criterion.passed:
                    st.caption(criterion.detail)

with col2:
    st.header("Active flags", anchor=False)
    render_flags(result.criteria, result.notices)

st.divider()

render_footer()
