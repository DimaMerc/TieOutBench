# Overnight reference value for ETF shares — prototype

The code behind the report `paper/etf-overnight-reference-value-v1.md`, *After the Close: What ETF Shares
Are Worth When Nobody Can Create or Redeem*. It measures where ETF shares trade overnight against what
their baskets are worth, for ten US funds over sixty nights, with a Frankfurt control.

Everything in the tables is real market data. Nothing is simulated. Where a value is a proxy (for
example the 4pm close standing in for the official NAV when no NAV file has been supplied), the record
says so in a `flags` field and the report says so.

## What it does, in order

1. **fetch** pulls, and caches to disk, the series a night needs: the fund's daily bars and its
   15-minute bars with pre- and post-market prints; hourly bars for the hedge instruments that trade
   through the night (index, Treasury and gold futures, bitcoin), the currencies and the local indices;
   5-minute bars for the hedge instruments; with a Tiingo key, the Blue Ocean overnight tape (8pm to
   3:59am) for the fund itself.
2. **build** assembles one record per fund per night: the 4pm close, the NAV (issuer file or proxy), the
   7:45pm sale, the static 20% overnight band the exchanges will publish, the hedge and currency moves
   at every hour from 8pm to 4am and at the close of every 5-minute overnight print, and the ground
   truth: the next morning's opening price. It estimates each fund's overnight beta on the nights
   *before* the test window and produces, for every hour of every test night, a reference value, an open
   band, a trip-wire status, and a trading band calibrated on the first half of the window and applied
   to the second.
3. **grade** scores it: error against the open, band coverage against its stated confidence, the two
   baselines that need no model (carry the 4pm value flat; the static band), and the distance of real
   overnight trades from the reference.
4. **report** writes `data/out/REPORT.md`.
5. **evidence** / **evidence-grade** (need keys): language models read the night's news for a fund's
   holdings and either raise a flag with citations and a direction, or say nothing material happened.
   They never propose a number. Graded against what the fund did at the open.
6. **hedge**: a model reads a fund's holdings and proposes hedge instruments from a fixed universe; a
   held-out test accepts or rejects the proposal. `--reevaluate` rescores saved proposals with no model
   call.
7. **frankfurt**: the control. UCITS funds on US indices on Xetra, in the hours before New York opens.
8. **publish** copies every cited statistic to `data/public/` with the market-data bars removed.

## Two rules the print statistics rest on

- **Same instant.** A 5-minute print is compared with the reference built from the futures bar that
  closes at the same moment, and never with a bar that was still open when the print closed. The public
  feed serves 5-minute futures bars for about its latest sixty trading days; on older nights only prints
  ending on the hour (where the hourly futures bar closes at the same instant) enter the distances.
  Each print carries `hedge_res`, `hedge_lag_s` and `aligned`.
- **Slots, not bars.** A session is 96 five-minute slots; a slot is traded when its bar shows volume.
  Feeds differ in what they return for a slot without a trade (Blue Ocean repeats the last price, Xetra
  returns nothing), so shares are counted against the session's slots.

## Running

```
cd prototypes/overnight
python selftest.py                                        # unit tests, no network
python run.py all --nights 60                             # fetch, build, grade, report on the latest window
python run.py evidence-grade                              # regrade saved model verdicts (no model calls)
python run.py hedge --reevaluate                          # rescore saved hedge proposals (no model calls)
python run.py frankfurt
python run.py publish
python tieout.py                                          # the report's tables against data/public
```

Every command takes two pins. `--end YYYY-MM-DD` fixes the last morning of the window. `--asof
YYYY-MM-DD` reads the feed downloads cached on that day and fetches nothing. The report's figures were
written by:

```
python run.py all --nights 60 --end 2026-11-06 --asof 2026-11-09
python run.py evidence-grade --end 2026-11-06 --asof 2026-11-09
python run.py hedge --reevaluate --end 2026-11-06 --asof 2026-11-09
python run.py frankfurt --end 2026-11-09 --asof 2026-11-09
python run.py publish
```

The public chart feed serves only its latest sixty trading days of intraday bars, so that exact window
can be rebuilt only from the downloads of November 9, 2026, which are the feed's data and are not in the
repository. On a later day the same commands, without `--asof`, measure a later window. `tieout.py` and
`selftest.py` need no data beyond what is committed.

Keys are read from the environment or the repo-root `.env` (gitignored), as the harness does:
`TIINGO_API_KEY`, `ALPHAVANTAGE_API_KEY` (or `ALPHA_VANTAGE_API_KEY`), and for the models
`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`. No key is written to disk by this code.
`python run.py keys` lists which names are visible and probes the paid endpoints without printing any
value.

Official NAV history: download the issuer's file in a browser (issuer sites do not serve these to
scripts) into `data/nav/` and run `python run.py nav`; it reads the iShares "Data Download" workbook and
the State Street "NAV History" workbook and writes `data/nav/<TICKER>.csv`. Without a file the 4pm close
stands in for the NAV and every record carries the flag `nav_proxy_close`. Issuer holdings files go in
`data/holdings/<TICKER>.csv`; `python run.py holdings` converts them.

## What is committed and what is not

| Path | In the repository | Why |
|---|---|---|
| `ovn/`, `run.py`, `selftest.py`, `tieout.py` | yes | the code |
| `data/public/` | yes | every statistic the report cites, as the commands wrote it |
| `data/holdings/*.json` | yes | the holdings lists shown to the models, with the news-ticker mapping |
| `data/out/` | no | working outputs, including the vendor's 5-minute overnight bars |
| `data/cache/` | no | downloads from the chart feed, the tape vendor and the news API |
| `data/nav/`, `data/holdings/*.csv` | no | the issuers' files as downloaded |

## Data labels used in records and reports

| Label | Meaning |
|---|---|
| `nav_proxy_close` | no NAV file; the 4pm close stands in for the official NAV |
| `nav_anchor_close` | the official NAV is struck at another hour (GLD), so the 4pm close is the anchor |
| `exdiv:<amount>` | the next morning is ex-dividend; the open is scored with the payout added back |
| `sale_1945_proxy_close` | no post-market print found before 7:45pm; the close stands in |
| `hedge_fallback:<sym>` | the preferred hedge instrument had no data; the named fallback was used |
| `signal_stale:<sym>` | the instrument's last closed bar was older than the staleness limit at that time |
| `truth_open_yahoo` | the ground truth is the 9:30 opening price as reported by the chart feed |

## Standard library only

Like the harness, this code uses only the Python standard library (`urllib`, `json`, `csv`,
`datetime`, `zoneinfo`, `statistics`). No pandas, no numpy. It is slower and plainer than it could be,
and anyone can run it.
