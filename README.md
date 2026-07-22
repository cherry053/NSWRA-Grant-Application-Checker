# Application-Checker
Updated version with upload pre-checks: a single-PDF upload (100MB limit) and
screening of the pasted damage table before the full analysis runs.

## How it works

The checker takes two inputs from the upload page:

1. **The SmartyGrants PDF export** of an EPAR application — exactly one PDF,
   up to 100MB. It is parsed up to the *Damage Information* section, and again
   from *Number of Damage Items* onward. The damage table pages in between are
   skipped — their rotated column layout does not survive PDF text extraction.
2. **The damage table as text** — the table copied out of the web form and
   pasted into the text box. This supplies the damage items the PDF cannot.

Both sources are parsed without regular expressions (anchor lines, ordered
cursor walks, and plain string operations only), merged, and run through the
validation rules: required fields, email/phone/date formats, NSW addresses and
coordinate bounds, cost component sums, evidence file naming
conventions and size limits, plus cross-document reconciliation of the damage
item count and the total amount requested.

Results are grouped into the six form-navigation sections (Grant Program
Information, Eligible Delivery Agency Details, EPAR Project Details, Damage
Information, EPAR Funding Request, Declaration and Authorisation), each an
expandable drop-down showing which criteria passed. Every criterion row and
section header carries a coloured status icon (green pass, orange review, red
fail), and the filter panel narrows the criteria list by status (Pass /
Review / Fail) and by a free-text search over the criterion name, section,
and detail. Raised flags are also shown as a ranked list of severity cards
(most severe first) on the results page, followed by INFO disclaimer cards
for selections the text export cannot show (Asset Material and the
pre-disaster function answer) — those ask the user to double-check manually
and never affect the confidence score or the overall status. The full
feedback, disclaimers included, can be downloaded as a PDF report.

Before the full analysis starts, the upload page screens the pasted table
(`core/paste_precheck.py`): it compares the number of complete pasted records
against the item count the PDF declares, and warns about an empty paste, more
than one pasted table (a repeated header row, duplicated damage item IDs, or
more records than the PDF declares), and a record cut off part-way through.
Column labels absent from the paste are reported as an informational note
only, since copying the table body without its header row is routine. The
warnings never block a check — the user can always run the full analysis
anyway — and field-level extraction
quality is still judged only by the validation criteria on the results page,
including *Damage Item Count Reconciles*.

Checking an application navigates to a dedicated Processing page that runs
the pipeline with a live staged progress checklist (Reading document →
Parsing application fields → Extracting damage table → Validating criteria →
Generating report) and a progress bar that advances page-by-page while the
PDF is read, then hands off to the results page. Each stage is held on
screen just long enough to be seen (about half a second) so the checklist
visibly plays through on fast checks; slow stages already exceed the minimum
and are never delayed.

The garbled damage-table pages are never extracted at all: `extract_pages`
reads the PDF top-down only until the *Damage Information* heading and
bottom-up only until the *Number of Damage Items* heading, skipping the
rotated table pages in between - which is where PDF text extraction spends
minutes on large applications. If either heading is missing, extraction
falls back to every page, so unusual exports are slower but never lose
content. The upload-time paste pre-check reuses the same fast extraction,
so screening the paste no longer freezes the upload page.

## Layout

- `core/pdf_extract.py` — PDF text extraction, page header/footer removal
- `core/section_splitter.py` — cuts the PDF at the damage table boundaries
- `core/field_parser.py` — application-level field parsing (labels, radios, checkboxes)
- `core/damage_table_parser.py` — damage-table text export parsing
- `core/paste_precheck.py` — upload-time screening of the pasted table against the PDF
- `core/validators.py` — all validation rules and scoring
- `core/filters.py` — criterion status mapping and results-page filtering
- `core/sections.py` — form-section constants and criteria grouping
- `core/report_pdf.py` — downloadable PDF feedback report
- `core/pipeline.py` — `check_application(pdf, table_text)` orchestration with staged progress
- `utils/ui.py` — NSW-branded rendering helpers (templates in `static/html`)
- `app.py` — upload form
- `pages/2_Processing.py` — dedicated loading page that runs the check
- `pages/1_Results.py` — results view with criteria filters and flag cards
- `pages/3_Guide.py` — in-app user instruction manual (assets in `static/guide`)

## Styling

The NSW Design System stylesheet (v3.24.10, MIT licensed) is vendored at
`static/vendor/` and served through Streamlit's static file route
(`server.enableStaticServing` in `.streamlit/config.toml`), so branding does
not depend on CDN availability inside firewalled networks. Application-specific
styles live in `static/css/main.css`.

## Running

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Tests

```bash
python -m pytest tests/
```
