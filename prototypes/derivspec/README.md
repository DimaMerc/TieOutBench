# derivspec: what a fund's documents settle, and what a language model does with the rest

When an exchange-traded fund that holds a derivative is set up on an accounting platform, someone writes the
processing requirements from the fund's documents. The documents do not state everything the system needs. This
prototype measures what language models do with the part that is missing, on three funds:

| key | derivative | documents (public) | what exists here |
|---|---|---|---|
| `swap` | total return swap in a leveraged fund | AdvisorShares MSOS Daily Leveraged ETF: annual report, prospectus, SAI | reference engine, 15 scenarios, 21 rules |
| `options` | four FLEX option positions in a buffer fund | Innovator U.S. Small Cap Power Buffer ETF - October: prospectus, SAI, annual statements | reference engine, 15 scenarios, 24 rules |
| `futures` | Treasury futures | Simplify Intermediate Term Treasury Futures Strategy ETF: prospectus, SAI, annual statements | 25 questions written before the documents were opened, and an answer key written afterwards |

The positions in the scenarios are constructed. The passages are the funds' own words (`docs/`, `docs_koct/`,
`docs_tya/`, each with an `INDEX.md` naming the document, its date and its address). The downloaded PDFs are not
redistributed (`sources/` is ignored).

## The four tests

1. **Drafts** (`draft.py`, `score_drafts.py`, `summary.py`). A model writes the requirements and the expected
   results of fifteen scenarios from the documents. Two task wordings: the task alone, and the task with one
   paragraph telling the model to say what each figure rests on. Three models, three runs each.
2. **A second reading** (`check.py`, `score_checks.py`). A reader gets the documents, the scenarios and one draft,
   or no draft, and says for every answer whether the documents settle it.
3. **Rule by rule** (`trace.py`, `score_trace.py`). A reader gets the documents and one neutral question per rule
   the system needs, and answers stated, partly, not stated or conflicting, with the passage word for word. Every
   quote is checked against the document text.
4. **The fair test** (the `futures` fund). The questions were fixed first, the fund chosen second, the answer key
   written third, the readers run last. `selftest.py` holds the fingerprint of the question list.

## The questions

[QUESTIONS.md](QUESTIONS.md) holds the three lists in full, 70 questions, each with what that fund's documents were
found to say. It is written by `python tieout.py questions --write` from the rule tables (`ds/rules.py`,
`ds/opt_rules.py`, `ds/fut_questions.py` with `ds/fut_key.py`).

## Two standards

Whether a rule counts as stated when the documents give the principle and not the mechanics was left open, so every
count exists twice (`ds/standard.py`): on the obvious reading (default; plain file names) and to the letter
(`DERIVSPEC_STANDARD=letter`; files ending in `.letter.json`).

## Two groups of gap

The report sets apart two groups of what the documents leave open (`ds/kinds.py`): terms and parameters (a day
count, the order of lots, a rounding, a threshold, the adjustment on a split) and accounting treatment (what is
recognized or realized, and when). The grouping was made after the second readings had been scored; it describes
the results and was not fixed in advance.

## Running it

```
python selftest.py                     # 1,142 checks; no network, no keys
python run.py gaps swap|options        # what the documents settle
python score_drafts.py && python summary.py
python score_checks.py
python score_trace.py
python tieout.py [--mutate]            # every figure and every general sentence of the report against the result files
python tieout.py questions [--write]   # QUESTIONS.md
```

The scoring commands read the saved answers under `data/out/` and need no keys. New model calls (`draft.py`,
`check.py`, `trace.py`) go through the repository's `harness.live` client with the caller's own API keys from the
environment; no key is stored. `collect_koct.py` and `collect_tya.py` rebuild the passages from the PDFs, for a
reader who downloads them.

## Where the answer key was corrected

The key is the fallible part. The docstrings of `ds/rules.py` and `ds/opt_rules.py` list three rounds of
corrections with the scores before each (`data/out/*.before_*`); `score_trace.py` records two questions of the
third fund where reading the readers' quotes showed the key to be wrong. That key was fingerprinted before the
readers ran and has not been changed.
