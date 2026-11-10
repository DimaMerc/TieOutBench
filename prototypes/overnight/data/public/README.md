# Published outputs

Every statistic cited in the report, as written by the prototype's own commands.

- `grades.json`: per fund, the open-based grading, the input facts (NAV against close, ex-dividend mornings, static band) and, under `overnight_prints`, the print statistics, the trading band and the late-print correlation.
- `fits.json`: betas, bands and windows. `nights_<FUND>.json`: every test night's reference values, bands, hedge returns, opening price and flags.
- `evidence_<FUND>.json`: every model verdict with its citation ids. `evidence_grades.json`: the grading, with `_second_stage` for the models that were run on the first model's flags.
- `hedge_proposals.json`: the model's proposals and their held-out scores. `frankfurt.json`: the Frankfurt control.
- `REPORT.md`: the same figures as tables.

Not here: the 5-minute overnight bars (Blue Ocean ATS through a vendor subscription) and the 15-minute Xetra bars are market data and are not redistributed, so the night files carry `prints: null` and a count. The open-based tables can be recomputed from these files; the print-based ones need the bars.

Written by `python run.py publish` after `run.py all --nights 60 --end 2026-11-06`, `run.py evidence-grade`, `run.py hedge --reevaluate` and `run.py frankfurt --end 2026-11-09`, from the feed downloads of 2026-11-09.
