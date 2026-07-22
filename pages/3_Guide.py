"""In-app user instruction manual, rendered as a standalone NSW-styled page.

The page is one HTML document injected through st.markdown: it hides the
Streamlit chrome and lays itself out with the locally vendored NSW Design
System stylesheet (no CDN fonts or icon fonts, so it renders inside
firewalled government networks like the rest of the app).
"""

import streamlit as st

st.set_page_config(page_title="User Instruction Manual | Grant Application Quality Checker", layout="wide")

st.html(
    """
    <style>
        /* Target the main content container */
        .stMainBlockContainer {
            max-width: 100% !important;
            padding-top: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
    </style>
    """
)
GUIDE_HTML = """
<link rel="stylesheet" href="/app/static/vendor/nsw-design-system-3.24.10.css">

<style>
/* Hide Streamlit chrome so the guide fills the window */
[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stHeader"],
[data-testid="stHeaderCollapsedControl"] { display: none; }
[data-testid="stMainBlockContainer"] { padding: 0; max-width: none; }
[data-testid="stAppViewContainer"] { border-top: none; }

/* Hide the anchor-link icon Streamlit adds next to headings */
[data-testid="stHeaderActionElements"] { display: none; }

/* Guide styles */
.nsw-header__logo-img { height: 75px; width: auto; margin-right: 1rem; }
.sidebar-sticky { position: sticky; top: 1rem; }
main figure img {
  max-width: 500px;
  width: 100%;
  height: auto;
  border: 1px solid var(--nsw-grey-04);
  border-radius: 4px;
}
/* Status pills in the results table */
.status-pill {
  display: inline-block;
  color: #fff;
  border-radius: 20px;
  padding: 4px 14px;
  font-weight: 600;
  font-size: 0.875rem;
  white-space: nowrap;
}
.status-eligible { background: #00843D; }
.status-manual { background: #C4780A; }
.status-noteligible { background: #B81237; }

/* In-page alert icons drawn as text glyphs (no icon font dependency) */
.guide-alert-icon {
  font-size: 1.5rem;
  line-height: 1;
  font-style: normal;
}

/* Accordion-style collapsible items (NSW look, no JS needed) */
.guide-faq {
  border: 1px solid #dee3e5;
  border-radius: 6px;
  margin-bottom: 0.5rem;
  overflow: hidden;
}
.guide-faq summary {
  list-style: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  padding: 1rem 1.25rem;
  font-weight: 600;
  color: #002664;
  cursor: pointer;
  transition: background 0.15s ease;
}
.guide-faq summary:hover { background: #002664; color: #fff; }
.guide-faq summary:hover::after { color: #fff; }
.guide-faq summary::-webkit-details-marker { display: none; }
.guide-faq summary::after {
  content: "\\25BE";
  font-size: 1.5rem;
  line-height: 1;
  color: #002664;
}
.guide-faq[open] summary { border-bottom: 1px solid #dee3e5; }
.guide-faq[open] summary::after { content: "\\25B4"; }
.guide-faq p { margin: 0; padding: 1rem 1.25rem; color: #495054; }
</style>

<!-- MASTHEAD -->
<div class="nsw-masthead">
  <div class="nsw-container">A NSW Government website</div>
</div>

<!-- HEADER -->
<header class="nsw-header nsw-header--simple">
  <div class="nsw-header__container">
    <div class="nsw-header__inner">
      <div class="nsw-header__main">
        <div class="nsw-header__image">
          <a href="https://www.nsw.gov.au/departments-and-agencies/nsw-reconstruction-authority">
          <img src="/app/static/guide/images/nsw-ra-logo.png" alt="NSW Reconstruction Authority logo" class="nsw-header__logo-img">
          </a>
        </div>
        <div class="nsw-header__name">
          <div class="nsw-header__title">Grant Application Quality Checker</div>
          <div class="nsw-header__description">NSW Reconstruction Authority &mdash; User Instruction Manual</div>
        </div>
      </div>
    </div>
  </div>
</header>


<!-- MAIN LAYOUT -->
<div class="nsw-container nsw-p-top-sm nsw-p-bottom-lg">
  <div class="nsw-layout">

    <!-- SIDEBAR -->
    <div class="nsw-layout__sidebar">
      <nav class="nsw-in-page-nav" aria-labelledby="in-page-nav">
        <div id="in-page-nav" class="nsw-in-page-nav__title">On this page</div>
        <ul>
          <li><a href="#before-you-begin">Before you begin</a></li>
          <li><a href="#step-1">1. Download the grant application as a PDF</a></li>
          <li><a href="#step-2">2. Upload your files</a></li>
          <li><a href="#step-3">3. Copy the Damage Information &ndash; EPAR table</a></li>
          <li><a href="#step-4">4. Paste the asset table</a></li>
          <li><a href="#step-5">5. Confirm and check application</a></li>
          <li><a href="#understanding-results">Understanding your results</a></li>
          <li><a href="#troubleshooting">Troubleshooting</a></li>
          <li><a href="#faqs">Frequently asked questions</a></li>
        </ul>
      </nav>
    </div>

    <!-- MAIN CONTENT -->
    <main id="content" class="nsw-layout__main">

      <div class="nsw-block" id="acknowledgement">
        <h1>User Instruction Manual</h1>
        <p class="nsw-intro">This guide explains how to prepare the required files and upload them to the Grant Application Quality Checker.</p>
      </div>

      <div class="nsw-block" id="before-you-begin">
        <h2>Before you begin</h2>
        <p>Before using the Grant Application Quality Checker, ensure you have completed the following:</p>
        <ul>
          <li>Access to your <strong>Essential Public Asset Restoration (EPAR)</strong> application in SmartyGrants.</li>
          <li>A <strong>PDF export</strong> of your completed grant application downloaded from SmartyGrants.</li>
          <li>The completed <strong>Damage Information &ndash; EPAR</strong> asset table copied from the application.</li>
          <li>Access to the <strong>Grant Application Quality Checker</strong>.</li>
        </ul>
        <p>The Quality Checker requires both the PDF application and the Damage Information &ndash; Asset Damage table to perform validation checks. Ensure both are available before proceeding.</p>

        <div class="nsw-in-page-alert nsw-in-page-alert--warning">
          <span class="guide-alert-icon nsw-in-page-alert__icon" aria-hidden="true">&#9888;</span>
          <div class="nsw-in-page-alert__content">
            <p class="nsw-h5">Important</p>
            <p>The Damage Information &ndash; asset damage table must be copied directly from the SmartyGrants application before running the quality check. Incomplete or missing information may result in validation errors or incomplete assessment results.</p>
          </div>
        </div>
      </div>

      <div class="nsw-block" id="step-1">
        <h2>1. Download the Grant Application As a PDF</h2>
        <ul>
          <li>Open your grant application in SmartyGrants.</li>
          <li>Click <strong>Download PDF</strong>.</li>
          <li>Save the PDF to your computer.</li>
        </ul>
        <figure>
          <img src="/app/static/guide/images/step1-download-pdf.png" alt="PDF download screen in SmartyGrants">
          <figcaption>PDF download screen</figcaption>
        </figure>
      </div>

      <div class="nsw-block" id="step-2">
        <h2>2. Upload Your Files</h2>
        <ul>
          <li>Open the Grant Application Quality Checker.</li>
          <li>Upload the SmartyGrants PDF.</li>
        </ul>
        <figure>
          <img src="/app/static/guide/images/step2-upload-pdf.png" alt="Uploading the PDF into the Grant Application Quality Checker">
          <figcaption>Upload PDF into checker</figcaption>
        </figure>
      </div>

      <div class="nsw-block" id="step-3">
        <h2>3. Copy the Damage Information &ndash; EPAR Table</h2>
        <ul>
          <li>Go to the Damage Asset Table section.</li>
          <li>Copy the table.</li>
        </ul>
        <figure>
          <img src="/app/static/guide/images/step3-damage-table-1.png" alt="Damaged asset table shown on SmartyGrants">
          <figcaption>Damaged asset table on SmartyGrants</figcaption>
        </figure>
        <figure>
          <img src="/app/static/guide/images/step3-damage-table-2.png" alt="Damaged asset table shown on SmartyGrants, continued">
        </figure>
      </div>

      <div class="nsw-block" id="step-4">
        <h2>4. Paste the Asset Table</h2>
        <ul>
          <li>Paste the damaged asset table into the text field in the Grant Checker.</li>
        </ul>
        <figure>
          <img src="/app/static/guide/images/step4-paste-table.png" alt="Pasting the asset table into the text field in the Grant Checker">
          <figcaption>Paste table into text field</figcaption>
        </figure>
      </div>

      <div class="nsw-block" id="step-5">
        <h2>5. Confirm and Check Application</h2>
        <ul>
          <li>Confirm that both the PDF and pasted text have uploaded successfully.</li>
          <li>Select <strong>Check Application</strong>.</li>
        </ul>
        <figure>
          <img src="/app/static/guide/images/step5-check-application.png" alt="Upload page showing PDF and text field upload">
          <figcaption>Upload page showing PDF and text field upload</figcaption>
        </figure>
      </div>

      <div class="nsw-block" id="understanding-results">
         <h2>Understanding Your Results</h2>
  <p>Each application is assigned a status after the quality check. The status helps you understand whether your application meets the checker's validation rules and whether any issues need to be addressed before submission.</p>

  <div class="nsw-table-responsive">
    <table class="nsw-table">
      <caption class="sr-only">Quality Checker result statuses and next steps</caption>
      <thead>
        <tr>
          <th scope="col">Status</th>
          <th scope="col">What it means</th>
          <th scope="col">What to do next</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><span class="status-pill status-eligible">PASS</span></td>
          <td>Your application meets all of the validation criteria checked by the Quality Checker.</td>
          <td>Review your application, then submit it through SmartyGrants when you are ready.</td>
        </tr>
        <tr>
          <td><span class="status-pill status-manual">REVIEW</span></td>
          <td>Some checks could not be verified automatically, or additional supporting evidence may be required.</td>
          <td>Review the flagged items and confirm they meet the grant requirements before submitting.</td>
        </tr>
        <tr>
          <td><span class="status-pill status-noteligible">FAIL</span></td>
          <td>One or more validation checks were not met.</td>
          <td>Correct the identified issues and run the Quality Checker again before submitting your application.</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="nsw-in-page-alert nsw-in-page-alert--info">
    <span class="guide-alert-icon nsw-in-page-alert__icon" aria-hidden="true">&#8505;</span>
    <div class="nsw-in-page-alert__content">
      <p class="nsw-h5">Note</p>
      <p>A PASS result means no issues were detected by the Quality Checker. It does not guarantee funding approval or eligibility. Applications are still assessed by the NSW Reconstruction Authority after submission.</p>
    </div>
  </div>
</div>

      <div class="nsw-block" id="troubleshooting">
        <h2>Troubleshooting</h2>
        <p>Answers to common issues when using the Grant Checker Tool.</p>

        <details class="guide-faq">
          <summary>No grants appear in my results</summary>
          <p>This usually means your project details are too specific for any current grant, or all relevant grant rounds are currently closed. Try broadening your project category, or check back when a new round opens.</p>
        </details>

        <details class="guide-faq">
          <summary>My ABN isn't recognised</summary>
          <p>Check that you've entered your ABN without spaces or dashes. If it's still not recognised, your ABN registration may be inactive — you can confirm this on the Australian Business Register.</p>
        </details>

        <details class="guide-faq">
          <summary>My results won't open or download</summary>
          <p>Make sure pop-ups aren't blocked in your browser for this site. If the problem continues, take a screenshot of your results as a temporary workaround and contact support using the details below.</p>
        </details>

        <details class="guide-faq">
          <summary>The tool has frozen or stopped responding</summary>
          <p>Refresh the page and start a new check. Your previous answers aren't saved automatically, so keep a note of your project details before you begin.</p>
        </details>
      </div>

      <div class="nsw-block" id="faqs">
        <h2>Frequently Asked Questions</h2>

        <details class="guide-faq">
          <summary>Does meeting the eligibility criteria guarantee funding?</summary>
          <p>No. The tool checks eligibility only, not the strength of your application. Grants are usually competitive, and meeting eligibility criteria doesn't guarantee funding.</p>
        </details>

        <details class="guide-faq">
          <summary>Can I run more than one check?</summary>
          <p>Yes. You can run as many checks as you like, for example if you're considering more than one project or want to check different funding amounts.</p>
        </details>

      </div>

    </main>
  </div>
</div>

<!-- FOOTER -->
<footer class="nsw-footer">
  <div class="nsw-footer__lower">
    <div class="nsw-container">
      <p class="nsw-footer__acknowledgement">We pay respect to the Traditional Custodians and First Peoples of NSW, and acknowledge their continued connection to their country and culture.</p>
      <hr>
      <div class="nsw-footer__info">
        <div class="nsw-footer__copyright">Copyright &copy; 2026</div>
      </div>
    </div>
  </div>
</footer>
"""

# Markdown treats lines indented 4+ spaces as code blocks, so flatten the indentation.
GUIDE_HTML = "\n".join(line.lstrip() for line in GUIDE_HTML.splitlines())

st.markdown(GUIDE_HTML, unsafe_allow_html=True)
