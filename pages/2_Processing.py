import logging
import time
from html import escape

import streamlit as st

st.set_page_config(page_title="Processing | Grant Application Quality Checker", layout="wide")

from core.pipeline import TOTAL_STAGES, check_application
from utils.ui import render_header

logger = logging.getLogger(__name__)

# User-facing checklist, aligned with core.pipeline._STAGES (one row per stage).
STEP_LABELS = (
    "Reading document",
    "Parsing application fields",
    "Extracting damage table",
    "Validating criteria",
    "Generating report",
)

# Minimum time each stage stays on screen. The pipeline usually finishes in a
# blink, which reads as a broken flash rather than a check happening - so fast
# stages are held just long enough to be seen. Slow stages already exceed the
# minimum and pay nothing, capping the total top-up at about two seconds.
MIN_STAGE_SECONDS = 0.45

render_header("Grant Application Quality Checker")

payload = st.session_state.get("processing_input")
if not payload:
    st.info("No application is currently being processed. Upload an export to begin a check.")
    st.page_link("app.py", label="Back to upload", icon=":material/arrow_back:")
    st.stop()

filename = payload.get("filename") or "your application"

st.markdown(
    '<div class="processing-hero" id="main-content">'
    f'<p class="processing-hero__file">Analysing {escape(filename)}</p>'
    '<p class="processing-hero__sub">Please wait while the checker validates your application&hellip;</p>'
    "</div>",
    unsafe_allow_html=True,
)

progress = st.progress(0.0)
checklist = st.empty()


def _render_steps(current: int, all_done: bool = False) -> None:
    rows = []
    for index, label in enumerate(STEP_LABELS):
        if all_done or index < current:
            state, icon = "done", "&#10003;"
        elif index == current:
            state, icon = "active", ""
        else:
            state, icon = "pending", str(index + 1)
        rows.append(
            f'<li class="processing-step processing-step--{state}">'
            f'<span class="processing-step__icon">{icon}</span>{label}</li>'
        )
    checklist.markdown(
        f'<ol class="processing-steps">{"".join(rows)}</ol>', unsafe_allow_html=True
    )


_render_steps(0)

_last_rendered_step = 0
_stage_shown_at = time.monotonic()


def _hold_stage_on_screen() -> None:
    """Keep the current stage visible for at least MIN_STAGE_SECONDS.

    Only tops up stages that finished faster than the minimum, so a slow
    document is never delayed - the pause exists purely so the checklist
    plays through instead of flashing straight to the results page.
    """
    shortfall = MIN_STAGE_SECONDS - (time.monotonic() - _stage_shown_at)
    if shortfall > 0:
        time.sleep(shortfall)


def _on_progress(step: int, total: int, message: str, stage_fraction: float = 0.0) -> None:
    # `stage_fraction` arrives once per extracted page during the reading
    # stage, so the bar fills as the parser works through the document; the
    # checklist only needs redrawing when the stage itself changes.
    global _last_rendered_step, _stage_shown_at
    if step != _last_rendered_step:
        _hold_stage_on_screen()
        _render_steps(step)
        _last_rendered_step = step
        _stage_shown_at = time.monotonic()
    progress.progress(min((step + stage_fraction) / total, 1.0), text=message)


try:
    result = check_application(
        payload["pdf_bytes"], payload["table_text"], on_progress=_on_progress
    )
except Exception as error:  # noqa: BLE001 - surface any parsing failure to the user
    logger.exception("Application check failed for %s", filename)
    checklist.empty()
    progress.empty()
    st.error(f"Could not check the application: {error}")
    st.page_link("app.py", label="Back to upload", icon=":material/arrow_back:")
    st.stop()

# Let the final stage and the fully ticked checklist be seen before leaving.
_hold_stage_on_screen()
_render_steps(TOTAL_STAGES, all_done=True)
progress.progress(1.0, text="Check complete")
time.sleep(MIN_STAGE_SECONDS)

st.session_state["check_result"] = result
st.session_state.pop("processing_input", None)
# The Results page caches its PDF report keyed by (application_id, scanned_at);
# scanned_at only has minute precision, so re-checking the same application
# within a minute would otherwise serve the previous report.
st.session_state.pop("_report_pdf_cache", None)

st.switch_page("pages/1_Results.py")
