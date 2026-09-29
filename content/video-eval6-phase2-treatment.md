# Video treatment: "I gave the AI the tools a desk has. Then a checker."

Working document for the eval-6 Phase-2 video (the follow-up to the 88-second TieOutBench video
published in September 2026). Same format that worked: presenter footage from the pilot pipeline
under `content/video/`, evidence cards cut in as B-roll, captions burned in, the MP4 uploaded
natively to LinkedIn with the YouTube link, evals.finance and the AI-likeness disclosure in the
first comment. Target length 90 to 100 seconds.

Status: the grid is run (2026-09-24): three arms, eight models, six cases, plus three repeats per
cell on the corrected dividend. Every figure below traces to `outputs/eval6-agent/` and is
reproduced by `python outputs/eval6-agent/summarize.py`. The findings are written up in
`outputs/eval6-agent/TAXONOMY.md`; nothing here goes beyond it.

## The subject the video has to explain

Three ideas, in this order, each with one picture:

1. **A document store, not a packet.** The desk gets an announcement, a correction, a position
   report and a distractor. Nothing says which one governs. Picture: the four document cards from
   `list_documents`.
2. **The position as of a date.** A dividend is owed to whoever held the shares on the record
   date. The correction moved that date by eleven days, and the account sold 10,000 shares in
   between. Ask for the position as of the old date and you get 50,000 shares; as of the new date,
   40,000. Picture: two `get_position` cards side by side, 50,000 and 40,000.
3. **The booking is the answer.** In the first evaluation the model wrote a plan. Now it books
   through a tool, and the grader reads the ledger, not the prose. A worksheet that says $6,800
   over a ledger that booked $8,500 fails. Picture: the ledger card next to the worksheet card,
   the tie-out line in red.

Then the experiment: the same six cases and eight models, three ways.

- **Plain**: the whole store in the prompt. The recorded runs from August.
- **Tools**: the model has to look things up, calculate, and book.
- **Checker**: a second agent of the same model, with the same look-up tools, receives only the
  work product (the worksheet and the ledger) and approves or rejects, with one revision round.

## What the runs say (the anchors, all from saved cells)

| Arm | clean runs of 48 | release-on-wrong-terms gate | any gate | source |
|---|---:|---:|---:|---|
| plain | 32 | 1 | 2 | `outputs/eval6-live/` |
| tools | 35 | 0 | 4 | `outputs/eval6-agent/tools/` |
| checker (same model reviews) | 27 | 0 | 8 | `outputs/eval6-agent/checker/` |
| checker-fixed (Opus reviews all) | 25 | 0 | 14 | `outputs/eval6-agent/checker-fixed/` |

- **The tool that prevents the error was there in every run.** The small model of the Phase-1
  finding was run five times through tools on the corrected dividend (`tools/gpt-5.4-mini/
  bry-dividend-2024/`, its `prior/`, and `repeat/tools/gpt-5.4-mini/bry-dividend-2024/r1` to
  `r3`). Twice it booked $8,500; both times it read the correction notice, called the calculator
  with 50,000 shares, and never called `get_position`. Three times it booked $6,800; each time it
  had asked for the position, as of the desk's own date, 2024-08-18, never the record date. Memo,
  verbatim from the first wrong run's ledger: "account position as of governing record date
  2024-08-23 not separately provided, so booked on store-determined entitlement basis from
  available position history and corrected terms."
- **Position-date discipline across the tools arm:** 48 of 48 runs read the governing document
  before acting; 37 of 48 asked for the position as of the entitlement's basis date; on the
  corrected dividend five models asked for both the old and the new date and booked on the new
  one; two runs never asked for the position at all.
- **The checker made the work worse.** Reviewers did the tie-out (48 of 48 queried the position,
  45 recalculated) and then rejected 20 of the 46 correct ledgers and approved one of the two wrong
  ones. The makers complied with 21 rejections; the revisions introduced four gates and five
  ledger faults that were not there before. Clean runs fell from 35 to 27. Two-by-two (round one,
  verdict against whether the ledger shown was correct): reject/wrong 1, reject/correct 20,
  approve/wrong 1, approve/correct 26.
- **A stronger reviewer did not fix it.** With one flagship reviewing every maker
  (`checker-fixed/`), the verdicts improved (13 correct ledgers rejected instead of 20) and the
  outcome did not (25 clean runs): ten of its rejections told the makers the fund is U.S.-domiciled
  so no withholding applies and the net equals the gross, every maker complied, and the fabrication
  gate fired ten times on answers that had been correctly held before the review. The line for the
  script: "The careful reviewer rejected less. It also told every model the answer to a question
  the documents do not answer, and every model wrote it down."
- **Repeats.** One model (Claude Sonnet 4.6) was clean twelve times out of twelve across the four
  arms. The small model landed on both sides of the finding in the tools arm. The reviewer of one
  mid-tier model gave three different verdicts on three identical correct ledgers.
- **Transport.** One flagship (GPT-5.6-sol) cannot use function tools on its vendor's compat
  endpoint and ran the text protocol; it was clean six of six. Say it once in the description.

## Scene plan

Durations are targets. Card ids refer to `storyboard.json` scene ids produced by
`python -m harness env --replay <cell> --cards`; presenter scenes come from the pilot pipeline.

| # | s | On screen | Narration (draft; plain prose, short sentences) |
|---|---|---|---|
| 1 | 0-5 | presenter | "Last time, an AI found the corrected dividend notice and still booked 8,500 dollars where 6,800 was due. This time I gave it the tools a desk has." |
| 2 | 5-14 | cards: `episode`, `step` list_documents, `step` read_document (the correction) from `tools/gpt-5.4-mini/bry-dividend-2024/prior/<run>/` | "Four documents. One is a correction that moves the record date by eleven days. The AI has to find that out on its own." |
| 3 | 14-24 | two `get_position` cards, 50,000 and 40,000 (from the oracle replay, labelled scripted, or from `tools/claude-opus-4-8/bry-dividend-2024/`, which queried both dates) | "And it can ask for the position as of any date. As of the old record date: fifty thousand shares. As of the new one: forty thousand. The right question is the whole job." |
| 4 | 24-34 | `ledger` card, `tieout` card | "Then it books. The grader reads the ledger, not the explanation. A worksheet that says six thousand eight hundred over a booking of eight thousand five hundred fails." |
| 5 | 34-46 | the arm grid card: 32, 35, 27 | "Eight models, six cases. Without tools, thirty-two clean runs of forty-eight. With tools, thirty-five. The wrong booking did not happen once in those forty-eight." |
| 6 | 46-58 | the five-attempt card for the small model: two wrong, three right; `position dates queried: none` on the wrong ones | "Then I ran the small model five times on the dividend. Twice it booked eight thousand five hundred. Both times it never asked for the position. When it asked, it booked right. The tool was there every time." |
| 7 | 58-72 | `review-1` card and the two-by-two card | "Then a checker: same model, same tools, only the work product. It rejected twenty of forty-six correct ledgers and approved one of the two wrong ones. The makers followed the bad findings. Clean runs fell from thirty-five to twenty-seven." |
| 8 | 72-84 | presenter + `grade` card | "Every run is saved: every tool call, every booking, every verdict. One run is a recorded result, not a rate. One model was clean nine times out of nine. The small one landed on both sides." |
| 9 | 84-95 | closing card "Does it tie out?" | "Cases, rubrics, transcripts and the leaderboard are public. TieOutBench, at evals.finance." |

## Rules for the script

- Every number traces to a saved run; every quoted model string is verbatim from that run's
  `transcript.jsonl` or `ledger.json`. Keep the file path beside each figure in the fact-anchor
  block of the post, as the September video did.
- Failure lines name the tier ("a small model", "a mid-tier model's reviewer"), never the vendor;
  the leaderboard card carries the names. Success lines may name the model.
- The events are real and cited to the filings; the accounts, positions and the ETF basket are
  constructed and disclosed. Say so once, in the description.
- Recorded runs, not deployment rates. One run per cell; the repeat runs on the dividend case
  measure repeatability, not production safety. The checker result is about one review protocol
  (same model, work product only, one revision round); say "this kind of checker", not "checkers".
- No employer names. The biography line stays as the September video has it.
- Plain prose. No flourishes, no fragment triplets, no "quiet". Re-read every time word on
  publish day ("last time", "in September", "in August").
- The AI-likeness and cloned-voice disclosure stays in the description and the first comment; the
  altered-content box stays ticked on YouTube.

## Production notes

- Cards: `python -m harness env --replay outputs/eval6-agent/<arm>/<model>/<case> --cards` writes
  `cards/NN-<scene>.png` at 1920 x 1080 in the house style (white, navy, green or red top bar by
  outcome). Scripted trajectories carry a SCRIPTED, NOT A MODEL RUN label; use them only to explain
  the mechanism (scene 3 may use the oracle's two position queries), never as evidence.
- The grid card (scene 5), the five-attempt card (scene 6) and the two-by-two card (scene 7) are
  built with a `make_*.py` under `assets/` the way the eval-6 hero was built, palette from
  `assets/make_hero_eval6.py`, numbers from `outputs/eval6-agent/summary.json`.
- The presenter passages (scenes 1, 8, 9) are new narration; the pilot pipeline's voice and
  likeness settings are unchanged (see `content/video/README.md` for the current version).
- Chapters (YouTube minimum ten seconds): 00:00 the tools, 00:14 the position as of a date,
  00:24 the booking is the answer, 00:34 what changed, 00:46 five attempts, 00:58 the checker,
  01:12 explore.
- Publish sequence: article first (so the link exists), then the video post with the link in the
  first comment; Tuesday to Thursday morning ET.
