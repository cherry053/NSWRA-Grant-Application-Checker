import logging

import streamlit as st

st.set_page_config(page_title="Grant Application Quality Checker", layout="wide")

st.html(
    """
    <style>
        /* Target the main content container */
        .stMainBlockContainer {
            max-width: 100% !important;
            padding-top: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            box-sizing: border-box !important;
        }
    </style>
    """
)
from core.paste_precheck import precheck_paste
from utils.ui import (
    render_cards,
    render_errormessage,
    render_footer,
    render_header,
    render_nosection,
    render_splash,
    render_uploadinfo,
)

logger = logging.getLogger(__name__)

render_splash()
render_header("Grant Application Quality Checker")

render_uploadinfo()

render_nosection()
render_nosection()

st.header("Upload SmartyGrants Export", text_alignment="center", anchor=False)

render_nosection()

with st.form("application_checker"):

    pdf_upload = st.file_uploader(
        "Drag and drop your PDF here",
        type=["pdf"],
        accept_multiple_files=False,
        help="Upload the SmartyGrants PDF export - one PDF file, up to 100MB.",
    )

    tabletext = st.text_area(
        "Enter Asset Damage Table information here:",
        help="Copy the damage table out of the web form and paste it here as plain text.",
    )

    submitted = st.form_submit_button("Check application")


def _start_processing(payload: dict) -> None:
    st.session_state["processing_input"] = payload
    st.switch_page("pages/2_Processing.py")


if submitted:
    # A fresh submission supersedes any earlier attempt that was held back
    # behind pre-check warnings.
    st.session_state.pop("pending_input", None)
    st.session_state.pop("precheck_warnings", None)
    st.session_state.pop("precheck_notes", None)

    table_text = tabletext.strip()
    if pdf_upload is None or not table_text:
        render_errormessage()
    else:
        payload = {
            "pdf_bytes": pdf_upload.getvalue(),
            "table_text": table_text,
            "filename": pdf_upload.name,
        }
        # Screen the paste against the PDF's declared item count before the
        # full analysis: an empty paste, a doubled-up paste, a truncated
        # record, or missing columns is cheaper to fix now than after a run.
        # This stays quick because extract_pages skips the garbled damage
        # table pages; the spinner keeps the page visibly alive meanwhile.
        with st.spinner("Screening the pasted table against the PDF..."):
            report = precheck_paste(payload["pdf_bytes"], table_text)
        if report.has_warnings:
            logger.info(
                "Paste pre-check raised %d warning(s) for %s",
                len(report.warnings),
                payload["filename"],
            )
            st.session_state["pending_input"] = payload
            st.session_state["precheck_warnings"] = report.warnings
            st.session_state["precheck_notes"] = report.notes
        else:
            # Informational notes (e.g. column labels absent because the table
            # body was copied without its header row) never gate the run.
            for note in report.notes:
                logger.info("Paste pre-check note for %s: %s", payload["filename"], note)
            _start_processing(payload)


if st.session_state.get("precheck_warnings") and st.session_state.get("pending_input"):
    for message in st.session_state["precheck_warnings"]:
        st.warning(message, icon=":material/warning:")
    for message in st.session_state.get("precheck_notes") or []:
        st.info(message, icon=":material/info:")
    st.caption(
        "Fix the pasted table and press 'Check application' again, "
        "or continue if this is expected."
    )
    if st.button("Run the full analysis anyway"):
        payload = st.session_state.pop("pending_input")
        st.session_state.pop("precheck_warnings", None)
        st.session_state.pop("precheck_notes", None)
        _start_processing(payload)


render_cards()

render_nosection()

render_footer()
