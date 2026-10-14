# SSRN submission package — the checker report (companion to TieOutBench v1.1)

Everything to paste into the SSRN submission form for the second paper. The PDF to upload:
`paper/tieoutbench-checker-v1.pdf`, built by `python paper/build_checker.py`.

## Title
A Second AI as Checker: Measuring a Maker-Checker Protocol for LLM Agents on Corporate-Actions Processing

## Author
Dmitry Krutous — Independent. Contact: welt.management.solutions@gmail.com · site: https://evals.finance

## Abstract
Paste the Abstract section of `paper/tieoutbench-checker-v1.md` word for word; the paper and the
SSRN page must match. Append, as the last line of the abstract field:

    Companion to the TieOutBench report, DOI 10.2139/ssrn.7243025. Every episode's transcript,
    ledger, worksheet, verdict and run record: https://github.com/DimaMerc/TieOutBench
    (outputs/eval6-agent/).

## Keywords
large language models; LLM agents; maker-checker; four-eyes control; corporate actions;
asset servicing; post-trade operations; LLM-as-judge; self-correction; sycophancy;
calibrated refusal; AI in finance; model validation

## JEL classification (suggested)
- G23 (Non-bank Financial Institutions; Institutional Investors)
- G28 (Financial Institutions and Services: Government Policy and Regulation)
- C52 (Model Evaluation, Validation, and Selection)
- C88 (Other Computer Software)
- M41 (Accounting) — the booking and ledger control

## SSRN network / category
Primary: Banking & Financial Institutions eJournal (as for the first report).
Cross-list: Econometrics: Computer Programs & Software eJournal; any "Artificial Intelligence"
or "Financial Technology" eJournal offered in the picker.

## Notes for the form
- Content Type: **Preprint** (a working paper not submitted to a journal is a preprint in SSRN's
  terms; do not choose "Other", which demands a free-text label and classifies the paper outside
  the preprint feeds).
- Profile requirement since 2026: an ORCID iD connected to the SSRN profile (or an institutional
  email). His iD: 0009-0003-7594-4671 (registered 2026-10-14; the first report is listed under Works).
- "Date written": October 2026.
- Reference URL field: https://evals.finance
- The paper carries the not-advice note in its front matter and the "Declaration on the use of
  generative AI" section; if the form has an AI-use question, answer yes and paste that
  section's first sentence.
- Related paper: link the first report's abstract page (7243025) in the "related papers" field
  if offered.
- Dataset: the Mendeley snapshot (10.17632/m5wfrnhdsp) predates `outputs/eval6-agent/`; either
  post a version 3 of the snapshot at the commit this paper is built from before submitting, or
  cite the GitHub repository only (the abstract line above does the latter). Decide before upload.

## Submission checklist
1. [ ] Build: `python paper/build_checker.py` (docx for review, pdf for upload); read the PDF once end to end.
2. [ ] Upload `tieoutbench-checker-v1.pdf`.
3. [ ] Paste title, abstract (+ the companion line), keywords, JEL codes.
4. [ ] Classify: Banking & Financial Institutions + cross-lists.
5. [ ] After acceptance: capture the abstract ID and DOI; add to docs/index.html (beside the first
       report), README.md (paper pointer), the paper's front matter in a v1.1 rebuild, and the
       LinkedIn profile's Publications section.
