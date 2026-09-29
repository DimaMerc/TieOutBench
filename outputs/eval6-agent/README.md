# outputs/eval6-agent — eval #6, Phase 2: the agent environment

The recorded runs of the three-arm comparison designed in
[`workflow/DESIGN-phase2-agent-environment.md`](../../workflow/DESIGN-phase2-agent-environment.md):
the same six corporate-actions cases and the same eight models as Phase 1, with the model working
through tools instead of reading the whole store in one prompt, and, in the third arm, a second
agent checking the work product.

| Arm | Where the runs live | What the model gets |
|---|---|---|
| plain | [`outputs/eval6-live/`](../eval6-live/) (Phase 1, unchanged) | the whole store in the prompt; writes the worksheet |
| tools | `tools/<model>/<case>/` | no store in the prompt; tools to list and read documents, query the position as of a date, calculate, book, escalate; then submits the worksheet |
| checker | `checker/<model>/<case>/` | the tools arm's work product, then a reviewer of the same model with the discovery tools that approves or rejects; one revision round |
| checker-fixed | `checker-fixed/<maker>/<case>/` | the same work products reviewed by one fixed model (Claude Opus 4.8) for every maker; the reviewer's model, transport and usage are in `run.json` under `reviewer` |

**Status: the grid is run (2026-09-24; the fixed-reviewer cells 2026-09-25).** 48 tools cells,
48 checker cells, 48 checker-fixed cells, and 96 repeats (three per model on the corrected
dividend in each of the four arms), no failures. The
findings, the trajectory rates, the reviewer two-by-two, the repeats and the grader log are in
[`TAXONOMY.md`](TAXONOMY.md); the tables are regenerated from the artifacts by
[`summarize.py`](summarize.py) (`--json` writes [`summary.json`](summary.json), `--details` adds
the per-cell trajectory tables). Headline: AllPass 32 (plain), 35 (tools), 27 (checker), 25
(checker-fixed, run 2026-09-25); `GATE.ELECT` 1, 0, 0, 0. The checker arm ran twice: the first wave's reviewer packet lacked the probe
question (its cells are preserved under each cell's `prior/` and under `repeat/checker-wave1/`);
the tables report the second wave. The conformance test passed on native function calling for
seven models; GPT-5.6-sol ran the text protocol (its vendor's compat endpoint refuses function
tools for it), disclosed per cell in `run.json`.

## What each cell contains

| File | What it is |
|---|---|
| `transcript.jsonl` | every message, tool call and tool result in order, with UTC timestamps, `finish_reason` and `usage` per turn |
| `ledger.json` | every ledger entry (voided ones marked), plus the frozen `ledger_v1` the reviewer was shown |
| `answer.json` | the submitted worksheet (graded by the unchanged Phase-1 grader: the arm-comparable number) |
| `terminal.json` | the worksheet with its action rows replaced by the ledger rows: the graded terminal state |
| `report.txt` | both reports, the ledger, the ledger verdict, the trajectory metrics, the review rounds |
| `run.json` | provenance: model, endpoint host, transport, budgets, usage totals, case/rubric/grader hashes, the score summary |
| `messages.json` | the maker's conversation (the checker arm continues it for the revision round) |
| `review.json` | checker arm: the review rounds and the ledger the reviewer was shown |
| `replay.md`, `storyboard.json` | the video pack (see `harness/env/storyboard.py`); `python -m harness env --replay <dir> --cards` adds PNG cards |

`conformance/<model>.json` records the per-endpoint conformance test that decides the transport
(native function calling, or the text protocol). `repeat/<arm>/<model>/<case>/r<n>/` holds the
repeatability runs. `prior/` under a cell holds the artifacts of any earlier run of that cell.

## Reading a result

Three layers per cell. The **worksheet** score is comparable across the three arms. The
**terminal** score is what the run is judged on in the tools and checker arms: GATE.ELECT fires on
what was booked, and a ledger flag (`ledger_inconsistent`, `ledger_empty`,
`ledger_missing_required`, `ledger_disallowed`, `ledger_contradiction`, `ledger_overescalate`)
zeroes the decision checkpoint. The **trajectory** block is reported, not scored: whether the
governing document was read before the first booking, which dates were passed to `get_position`,
whether `calculate` was used, and, for the reviewer, whether it recomputed or only read.

The reviewer two-by-two (verdict against whether the ledger it was shown was correct) is
assembled from `review.json` across cells; `ledger_shown_correct` is scored with the same
predicates as the final ledger.
