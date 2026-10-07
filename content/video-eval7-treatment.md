# Video treatment: "One swap at yesterday's price. May the NAV go out?"

Working document for the eval-7 video (the third in the format: the 88-second TieOutBench video of
September 2026 and the eval-6 Phase-2 video). Same format: presenter footage from the pilot
pipeline under `content/video/`, evidence cards cut in as B-roll, captions burned in, the MP4
uploaded natively to LinkedIn with the YouTube link, evals.finance and the AI-likeness disclosure
in the first comment. Target length 90 to 100 seconds.

Produced: `content/video/eval7-nav-v1/` (6 October 2026, 1:32.57). The recorded script is
`content/video/eval7-nav-v1/narrated-script.md`; where it differs from the scene plan below, the recorded
script is the reference (it corrected two overclaims in this draft: seven of eight paid models recomputed
51.9912, and the Qwen 27B break run took 24 minutes on a laptop).

Status: the paid grid ran on 2026-10-05 (eight models, two cases), the five open-weight local
models on 2026-10-05 and 2026-10-06, the six-attacker gaming review on 2026-10-06. Every figure
below traces to `outputs/eval7-live/` and is written up in `outputs/eval7-live/TAXONOMY.md`;
nothing here goes beyond it. Committed in 122344a.

## The subject the video has to explain

Three ideas, in this order, each with one picture:

1. **A NAV package, and one line in it.** The administrator's preliminary package for a 2x daily
   leveraged semiconductor ETF: a valuation ledger of eight lines, totals, the capital stock, and a
   pricing-exception report with one entry. Picture: the ledger card with the exception line
   highlighted: `line_id=SWAP-B flag=STALE_PRICE note=Westbrook valuation file not received by the
   17:30 ET pricing cut-off; prior business day (2026-06-22) value carried forward`.
2. **The statement is already in the package.** The counterparty's file arrived at 17:52 ET, after
   the cut-off but before the 18:00 release. It values the swap at 6,000,000; the ledger carries
   3,000,000. Picture: the two values side by side, 3,000,000 and 6,000,000, with the two times.
3. **Seventy-five cents.** Prior NAV 50.0000. The index rose 2.00 percent, so a 2x fund should move
   about 4.00 percent. The administrator's NAV is 51.2412, a move of 2.48 percent. Recomputed
   with the statement's value: 51.9912. The error is 0.75 a share, 1.44 percent, above the one-cent
   floor. The right call: hold, correct the mark, re-strike before 18:00. No shareholder
   reprocessing, because nothing was transacted at the wrong NAV. Picture: the NAV ladder,
   50.0000 at the bottom, 51.2412 and 51.9912 above it, the gap labelled 0.7500.

Then the experiment: eight paid models and five free ones, two packages each (the break, and the
same package with the file on time, which ties and must be released).

## What the runs say (the anchors, all from saved cells)

| Model | Tier | Break case | Clean case |
|---|---|---|---|
| Claude Opus 4.8 | flagship | 1.000 AllPass | 1.000 AllPass |
| Claude Sonnet 4.6 | mid | 0.972 | 1.000 AllPass |
| Claude Haiku 4.5 | small | 0.964 | 0.986 |
| GPT-5.6-sol | flagship | 1.000 AllPass | 1.000 AllPass |
| GPT-5.5 | flagship (previous) | 1.000 AllPass | 1.000 AllPass |
| GPT-5.4 | mid | 0.972 | 1.000 AllPass |
| GPT-5.4-mini | small | 0.633 | 1.000 AllPass |
| Gemini 3.6 Flash | small/fast | 0.956 | 1.000 AllPass |

Ten of sixteen AllPass; no gate fired; the release gate never fired. Source: `outputs/eval7-live/`,
matrix in `TAXONOMY.md`, scores after the 2026-10-06 re-grade (provenance in each `run.json`).

| Local model | Hardware | Break case | Clean case | Time |
|---|---|---|---|---|
| Qwen 3.8 27B (4-bit) | laptop 12 GB GPU + CPU (break); RTX 5090 (clean) | 1.000 AllPass | 0.986 | 24 min / 5.7 min |
| Gemma 4 31B (4-bit) | RTX 5090 | 1.000 AllPass | 1.000 AllPass | 5.7 / 6.3 min |
| Qwen 3.6 35B-A3B (4-bit) | RTX 5090 | 0.968 | 0.932 | 3.6 / 3.2 min |
| Qwen 2.5 32B instruct (4-bit, no thinking) | RTX 5090 | 0.535 | 0.941 | 2 min |
| Qwen 3.8 2B distill (8-bit) | laptop GPU | 0.131, sign gate | 0.174, false hold | 25 s |

- **Every paid model held the wrong NAV and released the clean one.** All eight named SWAP-B
  and ran the move check; seven of eight recomputed 51.9912. The dangerous thing, releasing the wrong NAV, did not
  happen once. Nobody held the package that tied.
- **The points lost were one layer below the decision.** The small OpenAI model (GPT-5.4-mini;
  unnamed in the script) summed the recomputed assets 2,000,000 short: corrected NAV 51.4912,
  error 0.25 a share, 0.49 percent, below the 0.5 percent reprocessing threshold. It held anyway,
  because the one-cent floor was exceeded either way. Two mid-tier models (Sonnet 4.6, GPT-5.4)
  computed 1.44 percent and answered the reprocessing test as "not exceeded"; Sonnet's own words:
  "Reprocessing is not applicable." The small Anthropic model (Haiku 4.5) ordered reprocessing of
  transactions that did not exist: "reprocess all transactions executed at the preliminary NAV of
  51.2412 to the corrected NAV of 51.9912" (verbatim, D1.escalate_to).
- **All eight refused the price question.** The fund's exchange closing price and its premium or
  discount are not in an accounting package. No model invented a price; none assumed the shares
  closed at NAV. One small, fast model's refusal reason was the answer form's own instruction
  text echoed back (Gemini 3.6 Flash, 0.956); the grader no longer credits that.
- **Two free models at the flagship level.** Gemma 4 31B passed everything on both packages in
  about six minutes each on the RTX 5090. Qwen 3.8 27B passed everything on the break case after
  24 minutes of thinking on the laptop (the clean case: 0.986 for a thin citation, 5.7 minutes on
  the 5090). The 2B distill read every line correctly and could not add them up: 108 million too
  high on the break case (NAV "overstated" by 27.75 a share, sign gate), 48 million too high on
  the clean one, which it held.
- **The grader was tested too.** Six attackers, one per grader surface, on 2026-10-06. Under the
  first grader, `RELEASE (see note)` scored 1.000 AllPass on the break case ("note" contains
  "not"); a fabricated price in the reasoning text passed as a refusal; a date with a time part
  lost 63 percent of the score. All fixed; 86 of their cases are standing checks; four scores
  moved on re-grade (Sonnet clean 0.957 to 1.000, GPT-5.4-mini 0.671 to 0.633, Qwen 2.5 0.558 to
  0.535, the 2B's clean case 0.212 to 0.174), none of them a decision or a gate.
- **Designed answers (the grader's own test, before any model ran):** every number right but the
  NAV released anyway 0.840 with the release flag; adopting the stale mark and releasing 0.354;
  reviewing the prior day's package 0.347; holding the clean package 0.840 with the decision step
  at zero (`workflow/nav-oversight-analysis.md`).

## Scene plan

Durations are targets. Cards are to be built (see production notes); presenter scenes come from
the pilot pipeline.

| # | s | On screen | Narration (draft; plain prose, short sentences) |
|---|---|---|---|
| 1 | 0-6 | presenter | "Every afternoon a fund's net asset value has to be checked before it goes out. I gave that check to eight AI models, and then to five free ones running on my own computers." |
| 2 | 6-16 | card: the ledger with the exception line highlighted | "The package has eight lines. One is a total return swap carried at yesterday's price, because the counterparty's file came in after the pricing cut-off. The exception report says so." |
| 3 | 16-26 | card: 3,000,000 beside 6,000,000, with 17:30 and 17:52 | "The file arrived at 17:52, after the cut-off but before the six o'clock release. It values the swap at six million. The ledger says three." |
| 4 | 26-38 | card: the NAV ladder 50.0000, 51.2412, 51.9912, gap 0.7500 | "The administrator's NAV is 51.24. The right one is 51.99. Seventy-five cents a share, above the one-cent floor. The right call is to hold it, fix the mark and re-strike before six. Nobody transacted at the wrong price, so there is nothing to reprocess." |
| 5 | 38-50 | card: the eight-model matrix, both cases | "All eight paid models held it, named the swap and recomputed 51.99. All eight released the clean twin package, where the file was on time. Ten of sixteen runs passed every check." |
| 6 | 50-62 | card: the small model's recomputation, 51.49 against 51.99, error 0.25 against 0.75 | "What went wrong was one layer down. One small model added the assets up two million short. Its error came out at twenty-five cents instead of seventy-five. It still held, because a penny was enough." |
| 7 | 62-74 | card: the local-model table, the two 1.000 rows highlighted | "Then the free models. A 31B from Google and a 27B from Alibaba did the same work: found the swap, recomputed the NAV, held. The 31B in about six minutes a case on a desktop graphics card; the 27B in 24 minutes on a laptop. A 2B could not add the lines up." |
| 8 | 74-86 | card: `RELEASE (see note)` -> 1.000 under the first grader, 0.840 with the release gate under the new one | "I also tested my own grader. Six AI reviewers tried to fool it. One found that RELEASE in brackets, see note, scored as a hold, because note contains not. Fixed, and now a standing check." |
| 9 | 86-96 | closing card "Does it tie out?" | "One break pattern, one run each. Cases, grader, every run and the reviewers' notes are public. TieOutBench, at evals.finance." |

## Rules for the script

- Every number traces to a saved run; every quoted model string is verbatim from that run's
  `answer.json`. Keep the file path beside each figure in the fact-anchor block of the post.
- Failure lines name the tier ("one small model"), never the vendor; the matrix card carries the
  names. Success lines may name the model (Gemma 4 31B, Qwen 3.8 27B). Scene 7 names the makers
  ("from Google", "from Alibaba") because it is a success line; drop the makers if it reads as a
  vendor comparison.
- The failure pattern is real and cited (Rydex CORRESP February 2024, Simplify QIS November 2024,
  AdvisorShares MSOX March 2026). The fund, the swaps, the counterparties and the administrator's
  package are constructed. Say so once, in the description.
- Recorded runs, not deployment rates. One run per model per case; one break pattern. The free
  models' result is "two of five on this package", not "free models are as good".
- No employer names. The biography line stays as the September video has it ("I led the delivery
  of an institutional ETF servicing platform: creation, redemption, corporate actions.").
- Plain prose. No flourishes, no fragment triplets. Re-read every time word on publish day
  ("every afternoon" is fine; nothing in the script is relative to the publish date).
- The AI-likeness and cloned-voice disclosure stays in the description and the first comment; the
  altered-content box stays ticked on YouTube.
- "51.24" and "51.99" in narration are the four-decimal figures 51.2412 and 51.9912 rounded for
  speech; the cards show four decimals.

## Production notes

- Cards: there is no replay tool for eval 7 (the eval-6 `harness env --replay` cards are for the
  agent environment). Build a `assets/make_cards_eval7.py` the way the eval-6 hero and the Phase-2
  grid cards were built: 1920 x 1080, white, navy, green or red top bar by outcome, palette from
  `assets/make_hero_eval6.py`. Inputs: `cases/grsl-nav-2026.case.yaml` (the ledger, the exception
  line, the statement values, the gold NAV ladder), `outputs/eval7-live/*/*/answer.json` (the
  small model's 51.4912 / -0.25; the matrix), `outputs/eval7-live/TAXONOMY.md` (the local table),
  `outputs/eval7-live/gaming-review/1-decision-classifier.md` (X1 for scene 8). Seven cards:
  ledger, two values, NAV ladder, matrix, small-model recomputation, local table, gaming card, plus
  the closing card from the September video.
- The presenter passages (scenes 1, 9) are new narration; the pilot pipeline's voice and likeness
  settings are unchanged (see `content/video/README.md` for the current version).
- Chapters (YouTube minimum ten seconds): 00:00 the package, 00:16 the statement, 00:26 seventy-five
  cents, 00:38 eight models, 00:50 one layer down, 01:02 the free models, 01:14 testing the grader,
  01:26 explore.
- YouTube title (draft, 70 characters): "One swap at yesterday's price. Would an AI release the NAV?"
- YouTube description (draft): "I gave eight AI models a fund administrator's preliminary NAV
  package for a leveraged ETF with one total return swap carried at the prior day's price, and then
  five open-weight models running on my own computers. Every paid model held the wrong NAV and
  released the clean one; two free models did the same. The errors were one layer down, in the
  arithmetic. The failure pattern is taken from SEC correspondence and issuer press releases; the
  fund, the swaps and the package are constructed. One run per model per case. Cases, grader,
  every run and the gaming-review notes: https://evals.finance and
  https://github.com/DimaMerc/TieOutBench. The presenter is my AI-generated likeness with a clone
  of my own voice."
- Publish sequence: article first (so the link exists), then the video post with the link in the
  first comment; Tuesday to Thursday morning ET, after the Phase-2 pieces have had their week.
