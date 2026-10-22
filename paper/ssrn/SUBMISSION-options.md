# SSRN submission package — the options-redemption report (third report in the TieOutBench series)

**STATUS: not yet submitted (drafted 2026-10-22). After approval: capture the abstract ID and, when assigned, the DOI;
fill the placeholder line "SSRN abstract and DOI: to be added when posted" in the paper's front matter, rebuild, and
thread the ID into docs/index.html, README.md and the LinkedIn Publications and Featured sections. The driver post
(content/linkedin-post-eval8-driver.txt) waits for the approval; its first comment takes the SSRN link.**

Everything to paste into the SSRN submission form. The PDF to upload: `paper/tieoutbench-options-redemption-v1.pdf`,
built by `python paper/build_options.py` (twelve pages, no figures).

## Title
Settle Only If Every Leg Ties: A Runnable Evaluation of Language Models on an Options-Component ETF Redemption

## Author
Dmitry Krutous — Independent. Contact: welt.management.solutions@gmail.com · site: https://evals.finance ·
ORCID 0009-0003-7594-4671

## Abstract
Paste the Abstract section of `paper/tieoutbench-options-redemption-v1.md` word for word (a verbatim copy is appended
at the end of this file by the build step; the paper and the SSRN page must match). Append, as the last line of the
abstract field:

    Third report in the TieOutBench series (the suite report, DOI 10.2139/ssrn.7243025; the checker report,
    DOI 10.2139/ssrn.7611299). Every run's answer, raw completion, scored report and run record, the six
    attacker notes of the grader review and the check of the fixture's mechanics against public documents:
    https://github.com/DimaMerc/TieOutBench (outputs/eval8-live/).

## Keywords
large language models; LLM evaluation; ETF creation and redemption; options clearing; FLEX options;
defined-outcome ETFs; post-trade operations; settlement tie-out; asset servicing; calibrated refusal;
adversarial evaluation of graders; AI in finance; model validation

## JEL classification (suggested)
- G23 (Non-bank Financial Institutions; Institutional Investors)
- G28 (Financial Institutions and Services: Government Policy and Regulation) — the NSCC and OCC rule filings
- C52 (Model Evaluation, Validation, and Selection)
- C88 (Other Computer Software)

## SSRN network / category
Primary: Banking & Financial Institutions eJournal (as for the first two reports).
Cross-list: Econometrics: Computer Programs & Software eJournal; any "Artificial Intelligence", "Financial
Technology" or "Market Microstructure" eJournal offered in the picker (the paper is about clearing-house
processing of ETF redemptions).

## Notes for the form
- Content Type: **Preprint** (same reasoning as before: a working paper not submitted to a journal; never
  "Other").
- ORCID iD connected to the SSRN profile: 0009-0003-7594-4671 (both earlier reports are listed under Works;
  Crossref's auto-update permission, granted from orcid.org, will add this one when its DOI is assigned).
- "Date written": October 2026.
- Reference URL field: https://evals.finance
- The paper carries the not-advice note in its front matter and a "Declaration on the use of generative AI"
  section naming the assistant, the six attacker sessions and the mechanics researcher; if the form has an
  AI-use question, answer yes and paste that section's first sentence.
- Related papers: link both earlier abstract pages (7243025 and 7611299) if the field is offered.
- Dataset: the Mendeley snapshot (10.17632/m5wfrnhdsp) predates `outputs/eval8-live/`; as for the checker
  report, cite the GitHub repository (the abstract line above does it) unless a new snapshot version is
  posted at the commit this paper is built from. Decide before upload.
- The fixture is constructed and says so; the abstract's sentence on labelled mechanics is the disclosure.
  If a reviewer asks, the mechanics note (`outputs/eval8-live/MECHANICS-NOTE.md`) lists every public
  document opened with its URL.

## Submission checklist
1. [ ] Build: `python paper/build_options.py` (docx for review, pdf for upload); read the PDF once end to end.
2. [ ] Upload `tieoutbench-options-redemption-v1.pdf`.
3. [ ] Paste title, abstract (+ the companion line), keywords, JEL codes.
4. [ ] Classify: Banking & Financial Institutions + cross-lists.
5. [ ] After acceptance: capture the abstract ID (and later the DOI); fill the front-matter placeholder and
       rebuild; add to docs/index.html (beside the two reports), README.md (paper pointer), the LinkedIn
       Publications section and a Featured card (SSRN gives LinkedIn no preview image: attach a 1200x630
       thumbnail as for the checker report); then publish the driver post with the SSRN link in its first
       comment.

## Abstract (verbatim copy, generated from the paper on 2026-10-22; 441 words)

When an exchange-traded fund whose portfolio is made of listed options is redeemed in kind, the option positions have to move at the clearing house from the fund's account to the redeeming dealer's account, and in 2026 that step still runs outside the clearing house's own process. In its rule filing of January 2026, NSCC describes it as "fragmented and heavily dependent on manual intervention, which increases the potential for errors." This report builds a runnable evaluation of that step and measures eight frontier models on it. The task is a settlement tie-out: given the redemption order, three portfolio composition files of which one is the basket of record, the fund's final net asset value, the clearing house's record of four position moves, the custodian's positions the next morning and the agent's own status report, tie every option leg to the basket, recompute the cash component, and decide whether to settle. The gold case has one leg moved at 12,000 contracts against 120 due, the order's underlying-share equivalent keyed as the contract count, while the agent's report says all four legs moved; the right answer is to hold and have 11,880 contracts returned first. A clean twin settles. Before any model ran, six independent attackers tried to make the grader score a wrong answer well or a right answer badly, about 1,500 graded mutations; every gate was then moved onto an evidence hook so that nothing fires on a missing field or a notation, and 267 of the attackers' checks were pinned as standing regressions. Every mechanical assertion of the fixture was checked against public primary documents and labelled. Then eight models from three vendors ran both cases once. Every model held the broken order and settled the clean one; nine of sixteen runs met every criterion; three models were perfect on both cases. The losses were arithmetic one layer down: a small model valued the option legs per share instead of per contract and fired the gate built for that confusion on both cases; a mid-tier model sized the excess at ten times its value; another moved the written legs' positions the wrong way; a small model converted a per-share impact to a percentage fifty times too small. No model assumed what the dealer had paid for its shares, though one stated its reason for refusing in the answer schema's own words. Running real models also found six places where the grader rejected legitimate answers; all runs were re-graded with the original scores kept, and eleven scores moved without any decision or gate changing. These are recorded results from one break pattern, one run per model per case, not rates.
