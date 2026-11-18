"""Two standards for "the documents state it", carried side by side.

  reading   the obvious reading: a rule counts as stated when the passages give the principle and the mechanics
            follow without a choice (the standard the rule tables were written to)
  letter    to the letter: a rule counts as stated only when a passage says it; where the passages give the
            principle and not the mechanics, the rule is "partly" stated

Which one is right for a fund administrator was left open on 2026-11-16, so every count is produced under both:
set the environment variable DERIVSPEC_STANDARD=letter to run a command to the letter. Result files written to the
letter carry ".letter" before ".json"; the files of the obvious reading keep their names.
"""
from __future__ import annotations

import os

NAME = os.environ.get("DERIVSPEC_STANDARD", "reading")
if NAME not in ("reading", "letter"):
    raise SystemExit("DERIVSPEC_STANDARD must be 'reading' or 'letter'")


def tag(name: str) -> str:
    """scores_swap.json -> scores_swap.letter.json when the run is to the letter."""
    return name if NAME == "reading" else name.replace(".json", ".letter.json")
