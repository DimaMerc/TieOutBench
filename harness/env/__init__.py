"""harness/env — the eval-6 Phase-2 agent environment (design: workflow/DESIGN-phase2-agent-environment.md).

An episode is one Phase-1 corporate-actions case held as three things: the document store
(unchanged, distractors included), a ledger (empty at the start, appended only through action
tools), and a clock (the case's `episode.as_of`). Tools are pure functions of the case file and the
ledger; nothing is fetched. Three arms share the six cases, the eight models and the grader:

  plain    the Phase-1 run (the whole store in the prompt; already recorded under outputs/eval6-live)
  tools    no store in the prompt; the model discovers, computes and books through tools, then
           submits the worksheet
  checker  the tools arm, then a second agent with the same discovery tools reviews the work
           product (worksheet + ledger, never the maker's transcript) and approves or rejects;
           one revision round

Scoring is deterministic and layered (harness/env/scoring.py): the worksheet through the UNCHANGED
Phase-1 grader; the ledger rendered into D1 action rows and passed through the same grader, so
GATE.ELECT fires on what was booked; ledger predicates that map onto the existing gates (the
consistency check "worksheet C1 must equal the booked amount", disallowed/contradictory/
over-escalating entries); trajectory metrics reported, never scored.

Modules:
  calc.py        the arithmetic-only calculator
  state.py       Episode: store, clock, ledger, transcript, the tool functions and their specs
  ledger.py      ledger entry -> D1 action row (what the Phase-1 hook scans)
  scoring.py     score_episode(): worksheet result, terminal result, ledger verdict, trajectory
  transport.py   native function calling over the OpenAI-compatible endpoints, the text-protocol
                 fallback, the per-endpoint conformance test
  agent.py       the maker loop, the reviewer loop, the maker-checker protocol
  oracle.py      scripted oracle trajectories per case + planted trajectories (the selftest)
  storyboard.py  transcript -> replay text, storyboard JSON and PNG cards (the video pack)
"""
from .state import Episode, MAKER_TOOLS, REVIEWER_TOOLS, ACTION_TOOLS
from .scoring import score_episode, render_episode_report
from .oracle import run_oracle, run_planted, PLANTED

__all__ = ["Episode", "MAKER_TOOLS", "REVIEWER_TOOLS", "ACTION_TOOLS", "score_episode",
           "render_episode_report", "run_oracle", "run_planted", "PLANTED"]
