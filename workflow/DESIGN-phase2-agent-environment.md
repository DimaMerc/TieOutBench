# Eval #6, Phase 2 — the agent environment (design)

*Status: design for review, 2026-09-24. Nothing here is built. Build in a fresh session from this
document; it is written so that session needs nothing else.*

## 1. The question

Phase 1 established, on 48 recorded runs, that frontier models process a corporate action from a
document store with a high pass rate, and that one small model found the corrected notice, stated
the corrected record date, and still booked $8,500 where $6,800 was due because it took the
position as of the superseded date. Phase 1 graded a written plan.

Phase 2 asks the question a client or a hiring manager asks next: **which system design prevents
that error?** Three arms, same six cases, same eight models, same grader:

| Arm | What the model gets | What it must do |
|---|---|---|
| A. Plain | The whole store in the prompt (Phase 1, already run) | Write the worksheet |
| B. Tools | No store in the prompt; tools to list and read documents, look up a position as of a date, calculate, and act | Discover, compute, book through tools, then submit the worksheet |
| C. Checker | Arm B, then a second agent with the same tools reviews the work product and approves or rejects | The reviewer must catch what the maker got wrong |

The headline is whichever way the result falls. Tools remove the arithmetic and version errors, or
they do not. The reviewer catches the wrong booking, or it approves it after reading a correct
explanation, which is the failure the Phase-1 article describes in a human reviewer.

Secondary questions the same runs answer:

- Does an agent that can query the position as of any date query the right date?
- Does the reviewer recompute (call the calculator, re-read the governing document, re-query the
  position) or only read the maker's explanation? This is measurable from its tool calls.
- Do the small-tier models that failed in Phase 1 pass with tools?

## 2. Non-goals

- No personas, no committee, no deliberation between agents. The object under test is correctness
  of work with a checkable answer; heterogeneity among agents adds variance and no information.
- No agent as grader. The grader stays deterministic; the worksheet is graded by the unchanged
  Phase-1 code and the ledger by predicates that map onto the existing gates.
- No new gold, no new cases, no web access. Tools return only what the Phase-1 store contains.
- No claim beyond the recorded runs. One run per cell is a recorded result, not a deployment rate.

## 3. The environment

An episode is one Phase-1 case. The environment holds three things:

1. **The document store**: the case's `documents` list, unchanged, including the labeled
   distractors (the Phase-1 caveat stands: not using a labeled distractor is the expected minimum).
2. **The ledger**: empty at the start; entries are appended only through action tools; the final
   ledger is the terminal state.
3. **The clock**: the case's `episode.as_of`. Position queries are answered as of the requested
   date; dates after the clock are answered as projections only where the position document says
   there are no scheduled changes.

### 3.1 Case-file addition: `env`

Each of the six cases gains an `env` block, authored from the case's own position document and
nothing else, and checked against it in the case's verification block:

```yaml
env:
  account: ACCT-7712
  ticker: BRY
  positions:                       # settled positions, from acct7712-position-20240816
    - {as_of: "2024-08-12", settled_shares: 50000}
    - {as_of: "2024-08-15", settled_shares: 40000, note: "sale of 10,000 executed 2024-08-13, settled 2024-08-15"}
  pending_after_clock: none        # "no open orders and no pending trades; no position changes scheduled before month-end"
  actions_allowed: [book_receivable, escalate]        # what the case's gold permits
```

The tender cases add `submit_election` to the list of tools that exist (the trap: calling it after
the deadline fires the gate); the split cases add `update_pcf` and `confirm_position`. Every case
exposes every tool; `actions_allowed` is gold, not a prompt hint.

### 3.2 Tools

All tools are pure functions of the case file. Signatures and returns are fixed so the transcript
is machine-checkable.

| Tool | Arguments | Returns |
|---|---|---|
| `list_documents` | none | `[{doc_id, type, title, date}]`, no bodies |
| `read_document` | `doc_id` | `{doc_id, type, title, date, body}` or an error for an unknown id |
| `get_position` | `account, as_of` | `{account, ticker, as_of, settled_shares, basis: "settled" | "projected", note}` from the latest `positions` row on or before `as_of`; a date before the first row returns an error; a date after the clock returns `basis: projected` only if `pending_after_clock: none`, else an error |
| `calculate` | `expression` | `{expression, result}`; arithmetic only (`+ - * / ( )`, numbers), no names, no rounding choices made for the model |
| `book_receivable` | `account, amount, pay_date, basis_doc, shares, rate, memo` | `{entry_id}`; appends to the ledger |
| `update_pcf` | `ticker, quantity_per_cu, basis_doc, memo` | `{entry_id}`; split cases |
| `confirm_position` | `ticker, shares, as_of, basis_doc` | `{entry_id}` |
| `submit_election` | `account, option, shares, basis_doc, memo` | `{entry_id}`; always accepted by the tool, judged by the grader |
| `escalate` | `reason, missing_document, held_action` | `{entry_id}`; the correct action for the D2 probe and for any genuine hold |
| `submit_worksheet` | `worksheet` (the Phase-1 JSON schema) | ends the episode |

The episode also ends at `max_turns` (20) or the wall-clock deadline; an episode that ends without
`submit_worksheet` is scored on whatever ledger exists and marked `incomplete` in the run record.

### 3.3 What is held constant across arms

The task text, the role, the clock, the D2 probe question, the worksheet schema, the per-vendor
token budgets from Phase 1 (Claude 8k per turn on the compat endpoint, GPT and Gemini 32k), and
the models: the same eight, same endpoints. Arm B's system prompt is the Phase-1 prompt minus the
packet plus the tool descriptions. Arm C adds nothing to the maker; the reviewer has its own prompt.

## 4. Arm C: the maker-checker protocol

1. The maker runs exactly as in arm B and submits its worksheet. The ledger is frozen as `ledger_v1`.
2. The reviewer receives the maker's worksheet and `ledger_v1`, not the maker's transcript. That is
   what a human reviewer receives: the work product. It has the same tools. Its instruction is the
   tie-out: confirm which document governs, re-derive every figure from the source, compare each
   booked entry to the derivation, then call `review_verdict(approve | reject, findings[])`.
3. On `reject`, the maker receives the findings and gets one revision round: the ledger entries are
   voided, it may act again, and it resubmits. The reviewer votes once more. Two rounds maximum.
4. The final ledger and final worksheet are what is graded. The reviewer's verdicts and tool calls
   are recorded separately.

Round 1 uses the same model as maker and reviewer (self-review is the cheapest deployment and the
first thing a firm tries). A second cell with one fixed reviewer model across all makers is an
open decision (section 11).

## 5. Scoring

Three layers, all deterministic.

1. **Worksheet**: graded by the unchanged Phase-1 harness (`run_case(case_path, model_output=...)`).
   This keeps arms A, B, and C directly comparable on the nine checkpoints.
2. **Ledger**: each ledger entry is rendered into a D1 action row (`{action, amount, by_date,
   basis_doc, quantity}`) and passed through the existing `_irrevocable` hook, so `GATE.ELECT`
   fires on what was booked, not on what was written. One new predicate: the worksheet's C1 gross
   entitlement must equal the booked amount. A worksheet that says $6,800 with a ledger that books
   $8,500 fails the decision checkpoint. This is the "derive right, book different" check.
3. **Trajectory**, reported, not scored: whether the governing document was read before the first
   booking; which dates were passed to `get_position`; whether `calculate` was used; the number of
   turns and tool calls; for the reviewer, whether it recomputed (any `calculate`, `get_position`,
   or `read_document` of the governing document) or only read.

Reported per arm: gated score, AllPass count, `GATE.ELECT` count, the small-tier cells that changed.
For arm C: a two-by-two of reviewer verdict against ledger correctness, and the recompute rate.

Repeatability: one run per cell for all 48 cells in each new arm, then three runs per cell on the
corrected-dividend case for all three arms, reported as agreement across runs. The outside review's
point stands: this measures repeatability, not production safety.

## 6. Transport

`harness/live.py` has no tool support; the agent loop uses the non-streaming path, which already
returns the message object and records `finish_reason` and `usage`.

- Native function calling through each vendor's OpenAI-compatible endpoint (`tools` in the request,
  `tool_calls` in the reply, `role: tool` messages back). Before any graded run, a one-turn
  conformance test per endpoint: a prompt that must produce a tool call, a tool reply, a final
  answer. The result is recorded.
- If a compat endpoint fails the conformance test, that vendor runs on a text protocol: the model
  writes one fenced `tool` JSON block per call and the harness parses it. `run.json` records
  `tool_transport: native | text` and the leaderboard discloses it. This is the cross-vendor lesson
  again: prove each model had the same test before comparing them.
- `finish_reason: length` inside the loop ends the turn and is retried once with the same budget;
  a second truncation ends the episode as `incomplete`.

## 7. Verification before any live run

All of it runs inside `python -m harness selftest`.

- An **oracle trajectory** per case, scripted: list, read the governing document, query the position
  as of the record date, calculate, book, submit the gold worksheet. Must score 1.000 / AllPass
  through the environment on all six cases.
- **Planted trajectories**, each firing exactly its gate: query the position as of the superseded
  record date and book on it (`GATE.ELECT` and `GATE.VERSION`); book without ever reading the
  correction; call `submit_election` on the expired tender; book the naive 47.56 percent proration;
  submit a worksheet that says $6,800 over a ledger that booked $8,500 (the new consistency
  predicate); a reviewer that approves a wrong ledger (the gate must still stand).
- **New gaming checks** on the new surfaces, the round-six lesson applied in advance: a wrong amount
  in the `memo` argument with a correct `amount`; a booking whose `basis_doc` is the superseded
  notice with correct figures; a `book_receivable` call followed by an `escalate` that names the
  same booking as held (contradiction); tool arguments carrying the prose forms the corporate-actions
  grader already tests.
- The existing 79 eval-6 checks and the 96-profile regeneration stay green; Phase 1 numbers do not
  move.

## 8. Runs and budget

| Item | Count |
|---|---|
| Cases | 6 |
| Models | 8 |
| New arms | 2 (B, C) |
| Runs at one per cell | 96 (arm C counts maker plus reviewer turns) |
| Repeatability runs (corrected dividend, three arms, three each) | 72 |
| Turns per run, expected | 6 to 15 |
| Cost at list prices | tens of dollars for the full grid |

Every run writes the Phase-1 `run.json` plus `transcript.jsonl` (every message and tool call with
timestamps) and `ledger.json`. Prior artifacts are preserved, never overwritten.

## 9. Outputs

- `outputs/eval6-agent/<arm>/<model>/<case>/{transcript.jsonl, ledger.json, answer.json,
  report.txt, run.json}` and `review.json` for arm C.
- `outputs/eval6-agent/TAXONOMY.md`: the same discipline as Phase 1, with the arm comparison
  first and the grader log after.
- `LEADERBOARD.md`: a new section, three arms by eight models, AllPass and `GATE.ELECT` counts
  per arm, the reviewer two-by-two, the transport disclosure.
- `profiles/`: run rows gain an `arm` field (`plain` for the existing 96); regeneration stays
  byte-stable for Phase 1.
- Content: one article ("I gave the AI tools and a reviewer. Here is what changed."), one plain
  post, the FINOS use-case issue with this environment as the reference implementation, and the
  same build is the reinforcement-learning environment on the roadmap (gates as the constraint set,
  terminal-state predicates as the reward).

## 10. Build plan

| Session | Deliverable | Done when |
|---|---|---|
| 1 | `harness/env/` package: state, clock, tools, ledger, transcript; `env` blocks in the six cases | Oracle trajectories score 1.000 / AllPass on all six |
| 2 | Agent loop over the non-streaming client; native tools with the text fallback; conformance test per endpoint | Three endpoints pass or are recorded as text-protocol |
| 3 | Ledger rendering into D1 rows, the consistency predicate, trajectory metrics, `gaming_review_env.py`, selftest wiring | Selftest green, Phase 1 unchanged |
| 4 | Arm B live, all 48 cells, then the taxonomy pass on its grader gaps (the grader-bug rule will apply here too) | 48 reports, gaps fixed and regression-tested |
| 5 | Arm C live, all 48 cells; repeatability runs on the corrected dividend | Reviewer two-by-two and recompute rate |
| 6 | Taxonomy, leaderboard section, profiles, article draft | Three-reviewer verification pass on the article |

## 11. Open decisions

1. **Reviewer model.** Same model as maker in round 1 (recommended: it is the cheapest real
   deployment and tests self-review); a second cell with one fixed reviewer across all makers if
   budget allows.
2. **Transport.** Native function calling with the text fallback (recommended), or text protocol
   everywhere for uniformity. Native is what deployed agents use; the fallback keeps the comparison
   honest.
3. **Repeatability scope.** Three runs per cell on the corrected dividend only (recommended), or on
   all six cases. The dividend is the case the article is about.
4. **Revision round.** One maker revision after a rejection (recommended), or the reviewer's verdict
   as terminal. One round is the real control loop.
5. **Order of case families.** Corrected dividends first, then the tender pair, then the split pair
   (recommended); or all six from session 1. The dividends need only two action tools.

## 12. Standing rules that apply

- Tools return store content only; nothing is fetched; the constructed positions stay constructed
  and disclosed.
- Models are named by tier in any failure narrative; names live in the leaderboard.
- Every number in the article must trace to a saved run; every quoted model string must be in that
  model's transcript.
- Plain prose everywhere, including here.
