TieOutBench v1 — evaluation suite, gold cases, and graded model runs (paper snapshot)

DESCRIPTION (paste into the dataset form)

This dataset is the exact repository snapshot behind the technical report "TieOutBench:
Measuring whether an LLM's finance work ties out - before deciding whether to trust it"
(SSRN abstract 7243025, August 2026). It is the state of the public repository at git commit
b965426 (2026-08-12), the version the report's numbers were produced from.

Contents:
- Five runnable evaluations of finance workflows: quarterly earnings analysis, buffer-ETF
  (defined-outcome) diligence, DCF valuation, ETF creation/redemption reconciliation, and
  OTC swap confirmation matching. Each is a workflow decomposition (workflow/), a point-weighted
  rubric with auto-fail gates (rubric/), and gold cases cited to source filings or labeled as
  constructed (cases/, 14 cases).
- The grading harness (harness/), pure Python with one dependency (pyyaml); `python -m harness
  selftest` reproduces the oracle and planted-error battery with no API key.
- Every graded frontier-model run reported in the paper: 48 runs (8 models from 3 vendors x 6
  cases on evals 3-5) plus the open-weight runs on evals 1-2, each with the raw completion, the
  parsed answer, and the scored report (outputs/), and the per-eval failure taxonomies.
- The report itself (docs/paper.pdf, paper/tieoutbench-v1.md) and the figure scripts.

Reproduce a published number: unzip, `pip install -r requirements.txt`, then
`python -m harness run --case mcd-fy2025-dcf --model oracle` (or any case) and
`python -m harness profiles` to regrade all committed runs.

The living repository, with later evaluations and grader revisions, is at
github.com/DimaMerc/TieOutBench (evals.finance). This snapshot is frozen on purpose so the
paper's figures stay reproducible after the repository moves on.

Not investment advice. Constructed elements (ETF baskets, custody accounts, counterparty legs)
are labeled as such in each case file; all event and filing figures are cited to their source.

SUGGESTED FIELDS
- Title: TieOutBench v1 - finance LLM evaluation suite, gold cases, and graded model runs
- Categories: Finance; Artificial Intelligence; Computer Science
- Keywords: LLM evaluation; benchmark; finance; post-trade operations; ETF; corporate actions;
  model validation; rubric; auto-fail gates
- License: MIT (matches the repository; CC BY 4.0 is the default offered - either is fine, MIT
  keeps it identical to GitHub)
- Related links: the SSRN abstract; github.com/DimaMerc/TieOutBench; evals.finance
- File: TieOutBench-v1-paper-snapshot-b965426.zip (4.2 MB)

AFTER IT IS APPROVED
- Add the dataset DOI to the SSRN record under Publication Details ("DOI referencing another
  version") and to the paper front matter at the v1.1 rebuild.
- Do NOT replace this dataset when eval 6 / round six are published; add a new version.
