# After the Close: What ETF Shares Are Worth When Nobody Can Create or Redeem

### Sixty nights of overnight trading in ten US ETFs, measured before the exchanges begin overnight sessions, with a Frankfurt control

**Dmitry Krutous**  
MBA, PMP · Independent · Greater Boston  
[evals.finance](https://evals.finance) · welt.management.solutions@gmail.com · ORCID [0009-0003-7594-4671](https://orcid.org/0009-0003-7594-4671)

*Version 1 (November 2026). This is a short technical report, the fourth in a series. The TieOutBench
report (SSRN, DOI [10.2139/ssrn.7243025](https://doi.org/10.2139/ssrn.7243025)) describes a suite of
runnable finance evaluations; the checker report (DOI [10.2139/ssrn.7611299](https://doi.org/10.2139/ssrn.7611299))
and the options-redemption report (DOI [10.2139/ssrn.7655899](https://doi.org/10.2139/ssrn.7655899)) grade
language models on ETF processing tasks. This report measures a market rather than a model: where ETF
shares trade, against what they are worth, in the hours when the mechanism that keeps the two together
does not operate. Every figure in it is written by the code in the accompanying repository,
[github.com/DimaMerc/TieOutBench](https://github.com/DimaMerc/TieOutBench), under `prototypes/overnight/`;
Section 10 says what a reader can and cannot regenerate, and why. SSRN: [to be assigned].*

*All market data in this report is real: exchange and venue prices from public and subscription feeds, net
asset values and holdings from the issuers' own published files. Nothing is simulated. Where a value stands
in for another, the text says so. Nothing here is advice regarding any security.*

---

## Abstract

On December 6, 2026 five US exchanges are due to begin trading 23 hours a day. Exchange-traded funds
already make up most of the small overnight market that exists today, and in those hours the arbitrage
that keeps an ETF's price at the value of its holdings does not operate: a creation or redemption placed at
night is an order for the next day's net asset value, no indicative value is updated, and the only
reference the exchanges will supply is a static band 20% either side of the close. This report measures how far prices move
from that value in those hours, before the market changes. For ten US ETFs over sixty nights, every five-minute bar of overnight trading
on Blue Ocean, the main overnight venue, was compared with a reference value built from the instruments
that do trade through the night: index, Treasury and gold futures, bitcoin, and the yen and euro. The
liquid funds trade at that value already, the S&P 500 fund within a median 2.4 basis points in every hour
of the night, with no creation window open. The funds holding foreign stocks and corporate bonds mostly
do not trade: in one five-minute slot in two hundred for Germany and one in eighteen for emerging markets.
When the foreign funds do trade, the prints are forty to sixty basis points from the reference, and the
evidence indicates that the reference is at fault, not the prints: the deviations predict the next morning's open,
and for emerging markets more than two fifths of the distance disappears once the Asian sessions, which a
futures-only reference ignores, are added. A reference value with two calibrated bands was built and tested out of
sample. The band for where a fund will open covers at close to the promised rate. The band for where it
should trade now is about ten times tighter for the liquid funds and holds only while volatility stays
where it was calibrated. Four language models reading the night's news for the funds' holdings added no
information beyond futures and the tape. A model choosing a fund's hedge instruments, scored on a held-out
test, improved the fit for Germany and for investment-grade credit, and its emerging-markets
proposal looked wrong only until the author's own measurement of it was corrected. A Frankfurt control,
nine Xetra-listed funds on US indices priced every morning while New York is closed, trades within two to
six basis points of futures-implied value on every listing, including listings that trade in a third of
the quarter-hours. A closed underlying does not move prices away from value where a futures hedge trades. What the
thin US funds lack at night is trading, and whether quoting obligations of the kind Frankfurt has would
supply it is a question this data cannot answer and the December sessions may.

---

## 1. Why an ETF price is right during the day

An exchange-traded fund has two prices.

The first is the net asset value, the NAV. It is the value of everything the fund holds, divided by the
number of shares, and the fund's administrator strikes it once a day, for most funds at 4pm New York time.

The second is the market price. It is whatever the last buyer and seller agreed on the exchange, and it
moves all day.

During the day the two stay close, and the reason is a mechanism called creation and redemption. A small group of
broker-dealers, the authorized participants, can hand the fund a basket of the stocks it holds and
receive new ETF shares in return, or hand back ETF shares and receive the stocks. If the ETF trades above
the value of its basket, they build baskets, create shares and sell them. If it trades below, they buy
shares and redeem them for stocks. Either way the gap closes. Market makers quote narrow spreads because
they know what the basket is worth from second to second and can hedge in the stocks. For many funds an
indicative value of the basket is also published every fifteen seconds through the trading day, although
since 2020 the exchanges' listing rules no longer require one for most ETFs [21].

That is the whole mechanism. It needs two things, and a third helps: the stocks must be trading, so the
basket has a price; the fund must be open to creations and redemptions, so a gap can be closed; and a
published number gives everyone the same thing to quote against.

At night none of the three holds in full. Overnight trading of US stocks and ETFs is not new. Blue
Ocean, an alternative trading system, has run a session from 8pm to 4am Eastern, Sunday to Thursday,
since 2021; retail brokers route overnight orders there, the demand is driven by retail investors in Asia
trading US names during their own daytime, and Jane Street, Virtu and Flow Traders are among its market
makers [1]. What trades at night is mostly ETFs: NYSE's research found exchange-traded products were 61%
of overnight trading against 21% in core hours [2]. BlackRock measured its iShares funds on Blue Ocean in
February 2025 and found spreads nearly ten times wider than in regular hours for the most active funds,
and as much as thirty times wider for some less frequently traded ones [3]. Those are facts about
spreads, the distance between the bid and the ask. They do not show whether the mid-price is close to
the value of the basket. This report measures that.

## 2. December 6

On Sunday December 6, 2026 overnight trading is due to expand from one venue to the exchanges. Five
exchanges, Nasdaq, NYSE Arca, Cboe EDGX, MEMX and 24X, have SEC approval or effective rules for a 23-hour
trading day. Each start is conditional on the consolidated data feeds being ready, so the date is the
expected one, not a fixed one [4, 5]. The overnight session runs from 9pm to 4am Eastern, after a
one-hour pause from 8pm on Monday to Thursday, and a trade made between 9pm and midnight carries the next
day's trade date [5, 6]. The consolidated feeds are due to extend their hours the same night [4]. NSCC,
the clearing house, has cleared from Sunday 8pm to Friday 8pm since June 29, 2026 [19].

Three details matter for ETFs.

**The official close stays at 4pm.** Overnight trades carry the extended-hours sale condition and are not
last-sale eligible; the listing exchange's closing auction at 4pm still sets the official closing price
[6]. The NAV is struck as before.

**The only overnight reference values are static bands.** Each listing exchange computes a lower band 20%
below the lower, and an upper band 20% above the higher, of the 4pm official close and the 7:45pm
consolidated round-lot sale, with each band at least three dollars from its reference price. The bands go
to the consolidated feeds by 8:55pm and stand unchanged from 9pm to 4am. Leveraged products get the
percentage multiplied by their leverage. The SEC's order calls the bands temporary, with a replacement to
be proposed [7]. They limit extreme prices; they are not estimates of value. In the sixty nights
measured here, the closest any opening price in the ten funds came to its band was 13 percentage points
away.

**The regulator has described the missing value and has not required one.** The SEC's order approving Nasdaq's overnight
session quotes the exchange's extended-hours disclosure rule, under which a broker must tell customers
that "the absence of an updated underlying index value or intraday indicative value" is a risk of trading
outside regular hours. A search of the order found no requirement that anyone supply such a value [5].
One data vendor sells a 24x5 reference price derived from quote and trade messages in the security itself
across exchanges, alternative trading systems and over-the-counter venues [9]. That measures where the
ETF is quoted and traded, not what its basket is worth, and the difference between the two is what this
report measures.

Meanwhile the primary market keeps its daytime schedule. Creation units are bought and redeemed at the
net asset value next computed after the order is received [11], so an order placed at 1am is an order
for that afternoon's NAV, and the basket file for the next day reaches NSCC by 10pm the night before
[10].

## 3. Data and method

**Three kinds of night.** The overnight problem depends on what a fund holds. *Night A*: the fund holds
US assets, and futures on its index, on Treasuries or on gold trade through the night and reflect most of
the information. *Night B*: the fund holds foreign stocks; Tokyo is open from about 7pm to 1:30am New
York time in winter and Frankfurt opens at 3am, so the basket is priced in its home market while the
fund's own market is closed. *Night C*: nothing trades, weekends and US holidays, or everything does,
bitcoin.

**Ten funds.** SPY, QQQ and SMH (US equity; SMH a concentrated semiconductor fund), EWJ, EWG and EEM
(Japan, Germany, emerging markets), TLT and LQD (long Treasuries and investment-grade credit), GLD
(gold) and IBIT (bitcoin). Hedge instruments: ES, NQ, NIY, ZB, ZN and GC futures, bitcoin spot, and the
yen and euro for the Japan and Germany funds. Emerging markets and Germany had no future on their own
index in the public feed and used S&P futures; Japan used Nikkei 225 futures, though the fund tracks a
broader index. Findings 3 and 7 show the effect of that.

**The window.** Sixty trading nights, from the evening of August 13 to the morning of November 6, 2026,
of which twelve span a weekend or holiday. Training data for the hedge relationships: the 434 nights
before that (437 for the bitcoin fund).

**The anchor.** Each night starts from the fund's 4pm value: the official NAV from the issuer's own
published file for seven funds; the 4pm close for QQQ and SMH, whose issuers' pages did not yield a
file, and for GLD, whose official NAV is struck off the London afternoon gold price rather than at 4pm
[12, 13]. Ex-dividend mornings are scored with the payout added back to the open, using the issuer's
ex-dates where the file provides them.

**The reference value.** The 4pm value moved by the hedge instrument's return since 4pm, scaled by a
beta estimated on the training nights, with the currency added for the Japan and Germany funds, computed
at every hour from 8pm to 4am and at the close of every five-minute bar of overnight trading.

**Two bands.** An *open band*: at each hour, the 90th percentile of the reference value's own error
against the next morning's 9:30 open on the training nights. A *trading band*: the 90th percentile of
the distance between the fund's traded overnight prints and the reference over the first thirty test
nights, by hour where the hour has at least thirty prints, applied to the last thirty.

**Ground truth.** The next morning's opening price, and every five-minute bar of overnight trading
from the Blue Ocean tape, August 13 to November 6, Sunday sessions included [14]. A night's session is
96 five-minute slots, and a slot counts as traded when its bar shows volume. The feed repeats the last
price through quiet slots and returns nothing before a session's first trade, so every statistic about
prints uses only bars in which shares changed hands.

**The same-instant rule.** A print is compared with the reference built from the futures bar that closes
at the same moment as the print, and never from a bar that was still open. The public feed serves
five-minute futures bars for about its latest sixty trading days, which covers the nights from August 31
(from September 11 for bitcoin). On the earlier nights only the bars ending on the hour, where the
hourly futures bar closes at the same instant, enter the distances; the other traded bars of those
nights, whose futures price would be up to 55 minutes older than the print, are counted as trades and
left out of the distances.

**Two baselines that need no model.** The static 20% band the exchanges will publish, and the flat
carry of the 4pm value through the night.

**Sources.** Futures, currencies, local indices and the funds' daily, 15-minute and 5-minute bars from a
public chart feed [20]; the overnight tape from Blue Ocean through a data vendor's subscription; NAVs,
ex-dividends and holdings from the issuers' files; news for the evidence layer from a market-news API.
The 7:45pm sale is the last post-market 15-minute bar before 7:45pm in the public feed, often the bar
ending at 7pm. Appendix A maps every figure to its source, and Appendix B lists what was not verified.

## 4. Findings

**Finding 1. The reference value beats carrying the 4pm value flat, in every fund.** Against the open,
the average error of the flat carry was 36 basis points for the S&P fund and 140 for the bitcoin fund;
the hedge-moved value cut those to 26 and 101. The improvement is largest where the hedge is best, the
S&P, Nasdaq, gold and bitcoin funds, whose betas sit near one with R-squared of 0.90 or better, and
smallest for emerging markets and Germany, where the hedge had to be S&P futures and R-squared fell to
0.39 and 0.55. Eight mornings in the window were ex-dividend, across four funds, with payouts of 10 to 43
basis points of the share price; scored without the payout added back, each would have looked like a
hedge error of that size. Two of the eight, a November ex-date for both bond funds, were in the issuers'
files and not yet in the market-data feed.

The issuer files showed which 4pm value to start from. For Japan, Germany and emerging markets the
official NAV is itself an estimate: the issuer fair-values the home-market close, by a median 29 to 59
basis points over the window, and by more than 400 for Japan and emerging markets on November 5, when
the US market fell more than four percent after Asia had closed. Starting from that NAV instead of the
close made the error against the next open slightly worse, 70 against 66 basis points for Japan, 57
against 55 for Germany, 89 against 88 for emerging markets, and the overnight prints sat further from a
NAV-anchored value than from a close-anchored one, 3.7 against 2.4 basis points for the S&P fund and 10.9
against 3.6 for bitcoin. Overnight prices follow the fund's own last trade, and the premium or discount at the close persists
through the night. The report therefore keeps two values: the official continuation from the NAV, graded
against the open, and the market continuation from the close, which the trading band and the print
comparisons use.

**Finding 2. The liquid funds already trade at the reference value.**

| Fund | Five-minute slots with a trade | Same-instant traded bars | Median distance (bps) | 90th percentile (bps) | Mean premium (bps) |
|---|---|---|---|---|---|
| S&P 500 (SPY) | 99.3% | 4,572 | 2.4 | 6 | +1.5 |
| Nasdaq 100 (QQQ) | 98.8% | 4,542 | 3.3 | 9 | +1.4 |
| Gold (GLD) | 98.5% | 4,570 | 2.6 | 7 | +2.0 |
| Bitcoin (IBIT) | 96.0% | 3,838 | 3.6 | 7 | -1.3 |
| Long Treasuries (TLT) | 84.6% | 3,951 | 4.9 | 16 | -2.4 |
| Semiconductors (SMH) | 92.6% | 4,263 | 23 | 73 | +5 |
| Japan (EWJ) | 18.9% | 855 | 41 | 86 | -10 |
| Emerging markets (EEM) | 5.5% | 262 | 62 | 140 | -20 |
| Investment-grade credit (LQD) | 2.3% | 113 | 6 | 24 | -4 |
| Germany (EWG) | 0.5% | 23 | 44 | 225 | -32 |

The S&P fund's distance from its reference is 2.2 basis points in the 8pm hour and 2.7 in the 3am hour,
and between the two in every hour in between. That is what prices set from futures alone would look like. The wide spreads measured elsewhere do not
mean that the mid-price is wrong. The investment-grade credit fund shows the same thing among the thinly
traded funds: it trades in about one slot in forty, and when it does it is six basis points from a
reference built on Treasury futures. A fund can trade rarely and still trade close to its value.

**Finding 3. Where the foreign funds trade far from the reference, the reference is the likelier source of the gap.**
The Japan, emerging-markets and Germany funds sat forty to sixty basis points from their reference when
they traded, with a negative mean of 10 to 32 basis points, and they traded in a small fraction of the
slots. Read alone, that looks like funds trading at a discount to their value. Two pieces of evidence
say otherwise. The first is Finding 4: the deviations predict where the fund opens, so the prints contain
information the reference lacks. The second identifies that information for emerging markets. That fund's
reference is built on S&P futures alone, while Hong Kong, Taipei, Seoul and Mumbai are open during the
US night. On the 25 nights with a late trade and all four Asian sessions available, the print's
deviation from the reference had a correlation of 0.72 with what those sessions add to the fund's
overnight move, the weights fitted on the training nights only. Taking that contribution out, the median
distance fell from 61 to 35 basis points and the mean from -23 to -5. More than two fifths of the
distance and most of the apparent discount came from leaving out markets that were open.

The same reading is likely for Japan, whose reference follows Nikkei 225 futures while the fund holds a
broader index that the Tokyo session prices directly, and it cannot be tested for Germany, which traded
in 23 same-instant bars in sixty nights. How much distance remains with a proper home-market reference is not
answered here; Section 8 describes the test.

**Finding 4. Thin-fund prints contain information; liquid-fund prints do not.** If the last trade before
4am sat above the reference, did the fund open above it too? For emerging markets the correlation
between the two deviations was 0.87 over 33 nights with a late trade, for Japan 0.61 over 51, for
semiconductors 0.61. For the S&P fund it was 0.20, on deviations of two to three basis points, and for
Treasuries, gold and bitcoin between -0.21 and 0.24. Where a fund trades rarely and the reference is
missing something, the few trades that happen show what it is; where a fund trades heavily, its trades
add nothing to what the futures already show.

**Finding 5. One band is not enough.** The open band covered the next morning's open between 84% and 95%
of the time across the ten funds, close to its 90% promise. But for the S&P fund its half-width runs from
79 basis points at 8pm to 63 at 4am, while the fund's overnight trades sit two to three basis points from
the reference; no same-instant trade in any of the six liquid funds fell outside it. It answers "where
will this open", which is the question for the 8:30am data releases and the pre-market. The trading band
answers "where should this trade now".

| Fund | Trading band half-width (bps) | Open band half-width, same hours (bps) | Prints covered, last 30 nights (promise 90%) |
|---|---|---|---|
| SPY | 6 | 72 | 89% of 2,818 |
| QQQ | 7 | 98 | 71% of 2,823 |
| GLD | 6 | 132 | 83% of 2,809 |
| IBIT | 9 | 224 | 94% of 2,744 |
| TLT | 14 | 74 | 87% of 2,616 |
| SMH | 53 | 220 | 77% of 2,714 |
| EWJ | 84 | 140 | 89% of 547 |
| EEM | 98 | 165 | 60% of 182 |
| LQD | not calibrated, 44 prints | | |
| EWG | not calibrated, 7 prints | | |

The S&P fund's trading band is six basis points either side of the reference, a twelfth of the open
band, and it held on 89% of the next month's prints. A published value with that band would describe
where the fund already trades. The band is not stable, though. For the Nasdaq, gold and
semiconductor funds it covered 71%, 83% and 77% of the later prints against a promise of 90%, because
the first thirty nights were calmer than the last thirty, which include the sell-off of early November:
the Nasdaq fund's median distance rose from 2.6 to 3.8 basis points between the two halves and the
semiconductor fund's from 18 to 25. A band calibrated in one month and left alone is too narrow for the
next when volatility rises, so a trading band has to be recalibrated on a rolling window or scaled by
the futures' own volatility. The emerging-markets band failed outright, covering six prints in ten, for
the two reasons already given: too few trades, and a reference that leaves out the markets that were
open.

**Finding 6. A news reader adds noise, not information.** A language model read every news item
published after 4pm about the ten largest holdings of each of the six equity funds, twice a night, at
1am and again at 4am, on all sixty nights: 120 readings per fund. It was told that most nights deserve
no flag and that it could only flag, cite, and name a direction, never a size. A reading counts as an
event when the fund opened outside the open band for that hour, a move the futures did not explain.

| Model | Readings flagged | Readings that were events | Precision | Recall | Direction right |
|---|---|---|---|---|---|
| Claude Haiku 5.5, SPY | 23% | 4% | 0.04 | 0.20 | 39% of 28 |
| Claude Haiku 5.5, QQQ | 38% | 7% | 0.07 | 0.38 | 50% of 40 |
| Claude Haiku 5.5, SMH | 45% | 17% | 0.24 | 0.65 | 64% of 53 |
| Claude Haiku 5.5, EWJ | 6% | 11% | 0.29 | 0.15 | 29% of 7 |
| Claude Haiku 5.5, EWG | 7% | 6% | 0.00 | 0.00 | 50% of 8 |
| Claude Haiku 5.5, EEM | 5% | 12% | 0.17 | 0.07 | 60% of 5 |

Restraint failed where news was plentiful: the model flagged almost one S&P reading in four and almost
every second semiconductor reading, nearly always citing a real after-hours event; the reading was right
and the judgment that it mattered beyond the futures was not. The foreign funds show the opposite
failure. The US news feed carried three hundred to six hundred items about their largest holdings over
the sixty nights, against fifteen thousand for the semiconductor fund, so the model stayed quiet and its
few flags often pointed the wrong way: it called a Sony earnings beat "up" on the night the Japan fund
opened 168 basis points below the reference.

Three more models were run on the 148 readings the first had flagged plus a fixed sample of 50 quiet
ones, 198 in all, of which 26 were events. Claude Sonnet 5.5 was more disciplined, keeping 56 of the 148
flags and raising none in the quiet sample, and right on direction in 37 of 52 calls, but the flags it
kept were events one time in eight and the flags it declined one time in seven: it caught 7 of the 26. A
two-billion-parameter model on a laptop answered 186 of the 198, the rest being too long for its
context; of the flags it kept, 9 in 34 were events, the highest rate of the four, but it broke the
output format on one answer in seventeen, cited an item that was not in its list in 5 of 46 flags, and
flagged a quarter of the quiet sample. A nine-billion-parameter model on the same laptop, which fits the
card only with its reasoning switched off, kept the format on every answer, flagged eight readings of
193, and caught one of the 26 events. Four models and one news source agree: reading headlines does not
show which nights the hedge will fail, and for the liquid funds the futures and the fund's own trades
already give the reference value.

**Finding 7. Where a model does help: choosing the hedge, with a held-out test deciding.** Each fund's
holdings, with weights, listings and country mix, were shown to Claude Sonnet 5.5 with a universe of 34
instruments that have overnight prices and their trading hours, and the model was asked to pick at most
four and weight them. The proposals were scored on the same 60 test nights against the hand-picked
hedge, out of sample, once with the model's own weights and once with weights fitted on the training
nights. It proposed no symbol that did not exist. For five funds it chose exactly what the prototype
already used, and for gold it added small silver and euro weights that changed nothing. For the S&P fund
it added a Nasdaq future and the fit edged from 0.977 to 0.981. For Germany it chose the DAX cash index,
S&P futures and the euro, and the fit rose from 0.550 to 0.865, and to 0.875 with the model's own
weights, the error against the open falling from 38 to 23 basis points; the DAX prices from 3am New York, so this
improves the morning estimate and not the midnight one, as the model's own rationale said. For
investment-grade credit it chose ten- and thirty-year Treasury futures with a small S&P weight, and the
fit rose from 0.74 to 0.84.

For emerging markets it chose four Asian cash indices weighted by country, and the first scoring
appeared to reject the choice: 0.17, against 0.46 for S&P futures alone on the same 47 nights. That
verdict was the author's error, not the model's. The first scoring measured each cash index from its
previous local close to its latest one, which also contains the index's reaction to the US session that
had just ended, something the fund's 4pm price already holds. Measured over the indices' own sessions
inside the night, the same four instruments score 0.37 alone, still short of S&P futures, and added to
S&P futures they lift the fit from 0.46 to 0.62 and cut the error against the open from 72 to 58 basis
points. Which of the two measurements to use is decided on the training nights, never on the test
nights: the training fit prefers the session measurement for the Asian indices and the
previous-close measurement for the DAX. The model proposes, a held-out test decides, and
two design rules follow: "baseline plus proposal, weights from the data", and "measure each instrument
over hours that match the fund's".

**Finding 8. The Frankfurt control: a closed underlying does not move prices away from value.** UCITS funds on US
indices trade on Xetra from 9:00 Frankfurt time, and until New York opens, usually at 15:30, their
underlying is closed while their own primary market is open and futures on their index trade. Nine such
funds were measured over 49 mornings, September 1 to November 9, 2026, against a reference anchored to
each fund's own previous last trade on Xetra and moved by S&P, Nasdaq or Russell futures and the euro,
with beta one and the currency one-for-one. A fitted beta did worse out of sample than that plain rule
on all nine.

| Fund | Index | Quarter-hours with a trade before the US open | Median distance (bps) | 90th percentile (bps) | Mean (bps) | Band from first half, coverage on second |
|---|---|---|---|---|---|---|
| iShares Core S&P 500 (SXR8) | S&P 500 | 100% | 2.1 | 5 | +0.1 | 8 bps, 99.7% |
| SPDR S&P 500 (SPYL) | S&P 500 | 99.8% | 2.5 | 8 | +0.2 | 9 bps, 97.6% |
| iShares Core S&P 500 Dist (IUSA) | S&P 500 | 98.0% | 3.0 | 9 | 0.0 | 11 bps, 98.1% |
| Vanguard S&P 500 (VUSA) | S&P 500 | 92.0% | 3.1 | 10 | -0.4 | 12 bps, 96.1% |
| Invesco EQQQ (EQQQ) | Nasdaq 100 | 90.7% | 5.2 | 15 | -0.4 | 20 bps, 98.6% |
| SPDR Russell 2000 (ZPRR) | Russell 2000 | 83.2% | 5.3 | 14 | +0.6 | 16 bps, 96.0% |
| Xtrackers S&P 500 Swap (D5BM) | S&P 500 | 56.2% | 5.2 | 15 | +0.1 | 20 bps, 98.9% |
| Amundi Core S&P 500 Swap (LYPS) | S&P 500 | 42.3% | 3.7 | 11 | +0.8 | 12 bps, 96.6% |
| HSBC S&P 500 (H4ZF) | S&P 500 | 32.1% | 6.4 | 17 | +1.9 | 17 bps, 87.3% |

The most traded S&P 500 fund in Frankfurt sits a median 2.1 basis points from futures-implied value,
flat from 9am to the US open. That is the same result as for the S&P fund on the US overnight venue, in another
currency and under another market structure. The control supports two
statements. First, a closed underlying does not by itself move an ETF's price away from its value: where a future on
the fund's index trades, the price follows it to within a few basis points. Second, that holds for
listings that trade rarely. The thinnest S&P 500 listing here trades in a third of the quarter-hours and
still sits a median 6.4 basis points from the reference, as the credit fund does on the US night.

What the control cannot do is say why the foreign funds trade so little on the US night. Counted the
same way, in quarter-hours, the Japan fund traded in 41% of them, emerging markets in 14%, credit in 6%
and Germany in 1.4%. Frankfurt differs from the US night in at least four ways at once. A Xetra ETF in
continuous trading needs at least one Designated Sponsor, who must quote in at least 80% of effective
trading time each month within a maximum spread and a minimum quote size set for that product, and who
loses the mandate in that fund after six consecutive months below the minimum [15, 16]; Blue Ocean's
2021 regulatory filing discloses no liquidity-provider arrangements and its published trading rules
describe no quoting obligation [22], and on Nasdaq a market maker's obligation to quote both sides applies
"during regular market hours", which the SEC's order for the night session leaves unchanged [5, 23]. The
Frankfurt funds' primary market is open during the hours
measured. Their hedge is a future on their own index. And the Frankfurt morning is those listings' main
session, not an off-hours one. The data cannot separate these four, and a tape of trades cannot show
whether quotes were there and unused. Quoting obligations are the one of the four that the exchanges
opening overnight sessions on December 6 could choose to add, which makes it the one worth watching.

## 5. What a reference value should be

In plain words: a best estimate of what the basket is worth right now, two calibrated ranges around it, and
a one-line reason for every change, with its purpose stated per fund.

1. **Start from the 4pm value**, the official NAV where the issuer's NAV is a 4pm value, and the 7:45pm
   sale the exchanges already use.
2. **Move it by what has actually traded since.** Index, Treasury, gold and bitcoin prices through the
   night, currencies, and, for foreign holdings, the home markets while they are open, each measured
   over hours that match the fund's and weighted on the fund's own history. Finding 3 is the reason the
   home markets have to be included.
3. **Blend in the fund's own last trade where it is informative.** For the thin funds the last print
   predicts the open; for the heavily traded funds the print adds nothing to the futures.
4. **Read the news for the morning report, not for the number.** Finding 6 is the reason.
5. **State two ranges.** The open band for where the fund will open; the trading band, calibrated on the
   fund's own prints and recalibrated as volatility changes, for where it should trade now.
6. **A rule for when the value is not usable.** Inside the trading band the number is usable; outside it, or when an input is stale,
   the value is marked unreliable and both bands widen. The precedent is the SEC's February 2026 order
   that lets dealers transact in a tokenized government money market fund at one dollar instead of the
   next NAV, on conditions that include a daily market-based NAV: under the application's conditions, a
   deviation of 0.25% or more suspends the one-dollar dealing or moves it to the next calculated NAV
   [17].
7. **Keep the record.** Every night's values, inputs, trades and the next morning's official NAV, so the
   value can be graded.

## 6. Where a model belongs, and where it does not

The quantitative steps need no language model, and the data shows it: the liquid market already
does step 2 to within two to five basis points without one. The one step where a model improved the
number is Finding 7, choosing the hedge instruments with a held-out test deciding, where it never
invented a symbol, improved two funds, and proposed for a third the instruments the reference was
missing, once they were measured correctly. The places it belongs otherwise are the
places where it reads and something exact grades the reading: extracting scheduled events from issuer
notices, ex-dates, amounts, rebalances, local holidays, where the answer key is exact and small issuers
have no feed; writing the morning report from the night's record with every number and citation checked
against that record; mapping local tickers to the listings a news feed understands. None of these asks
the model what will happen to a price. Finding 6 asked that of four models, and none could answer it.

## 7. Who would use it

For the liquid funds the level is already in the prices, to within two or three basis points, so market
makers there do not need it. The people without a number are everyone else:
an issuer cannot see how far from basket value its Germany fund traded at 1am, and neither can the
investor who traded it. The required disclosures do not cover it either. Rule 6c-11
requires every ETF to publish its premium and discount history measured where the NAV is struck, from
the official closing price or the bid-ask midpoint at that time [18], so overnight trading does not appear
in it, and after December 6 a board may reasonably ask what happens to its funds at night. Section 4
shows what the answer looks like once someone measures it. Exchanges could replace static bands with bands
that update; in this window the static ones were never close to binding.

For a fund administrator, which already strikes the NAV and prepares the premium and discount tables for
the issuer, three tests decide whether this is a service: whether it runs on data the administrator
holds, which it mostly does; whether it earns a fee or cuts a cost, which is the open one, the case for
it being a feature clients come to expect rather than a product they ask for; and whether it leaves the
fiduciary decision with the adviser, which it must, the value being indicative and the methodology
signed by the valuation designee. In the author's view the first product that passes all three is not a
published number. It is a morning report: how many slots a fund traded in, how far from the reference,
how good the reference is for that fund, and whether the static band ever mattered. The Frankfurt
control adds the question to ask about any venue a fund trades on: what supports the prices there,
a hedge on the fund's own index, an open primary market, an obligation to quote.

## 8. Limitations

One venue and one period. Everything measured on the US side is Blue Ocean, Sunday to Thursday, before the
exchanges began overnight sessions; the exchange sessions will have more venues and the funds' own stocks
trading overnight for the first time, and may have quoting obligations of their own, although Nasdaq's
approved rules add none. December 6 is the expected
start, not a certain one.

Trades, not quotes. The tape has no order book, so the report cannot say whether a thin fund had a
two-sided market that nobody used or no market at all, and it measures no spreads.

Sixty nights. The test window was calm for the S&P fund relative to its two-year history and volatile for
semiconductors, and its second half contains the early-November sell-off, including a fall of more than
four percent on November 5; the trading-band evaluation sits in that half.

The references for the three foreign funds are weak, and their distances and discounts are distances
from a weak reference. Emerging markets and Germany are hedged with S&P futures, Japan with Nikkei 225
futures against a fund on a broader index, and the hedge is measured to 9:00 against a 9:30 open. The
test that would settle Finding 3 is to rebuild each foreign fund's reference from home-market prices at
each print's own time and see what distance and what mean remain, split by hour and by whether the home
market was open.

The same-instant rule leaves out the traded bars of the first twelve nights that do not end on the hour
(the first twenty for bitcoin), because the public feed no longer serves five-minute futures bars for
them. Those nights are in the open-based grading in full.

The trading band was calibrated and tested inside the same sixty nights, the first thirty against the
last thirty, because the tape begins in August. The emerging-markets comparison in Finding 7 covers 47
of the 60 nights, those on which all four cash indices have bars, for the proposal and for the baseline
alike.

The evidence layer is one news source queried by US ticker or ADR, so about 14% of the emerging-markets
fund, Samsung, SK Hynix, MediaTek, Reliance and Bharti, had no news in the sample at all. The holdings
shown to the models are the funds' holdings of early November, used for all sixty nights. The event
definition sets the base rate at about one reading in ten by construction; sign accuracy does not depend
on it and points the same way. The nine-billion-parameter model ran without reasoning, the only setting
that fit a 12 GB card, while the cloud models ran with their defaults. The local-model samples are
small. SPY's first-stage verdicts were generated twice after a file collision and rest on a mix of
first-run and re-run answers from the same model and prompt.

The Frankfurt control is 49 mornings, nine funds and one rule. Its feed returns a bar only when
something traded, and each print is measured against the fund's own previous last trade moved by
futures, so two prints' errors enter each distance; dividends for the distributing funds come from the
market-data feed; two of the funds are swap-based. The statement about Blue Ocean rests on its 2021
filing and its published rules; later amendments were not read, and it is the author's reading of public
material, not a statement from the venue.

The anchor for GLD is the 4pm close because its official NAV is struck off the 3pm London gold price,
10am in New York; the official NAVs used for the other seven funds come from the issuers' published
histories as of November 6, 2026.

## 9. What happens next

From December 6 the same code captures the exchange sessions night by night, with Frankfurt running
alongside as the control. Three things are worth measuring in the new regime: whether the thin funds
start to trade; whether, with a reference rebuilt from home-market prices, any distance or discount
remains for the foreign funds; and whether the exchanges attach quoting obligations to their overnight
sessions, which Nasdaq's approved rules do not, and, if any do, whether trading in the thin funds follows. Sixty nights of the new regime
reach into early March 2027.

## 10. Reproducibility

The prototype is under `prototypes/overnight/` in the repository and uses only the Python standard
library. `run.py all --nights 60 --end 2026-11-06` fetches the public feeds, builds the nights, grades
and reports; `run.py nav` and `run.py holdings` convert the issuers' files; `run.py evidence` runs the
news-reading models through the repository's provider-neutral client and `run.py evidence-grade` grades
them; `run.py hedge` runs the proposer and its held-out test; `run.py frankfurt --end 2026-11-09` runs
the control; `selftest.py` checks the pure parts without a network. Every statistic in this report is
written by those commands to `data/out/` as JSON and copied by `run.py publish` to `data/public/`, the
committed copy, with every night's inputs, every model verdict and every citation id.

What a reader can regenerate depends on the data, not on the code. The public chart feed serves only its
latest sixty trading days of intraday bars, so this report's window can be rebuilt bar for bar only from
the downloads cached on November 9, 2026 (`--asof 2026-11-09`), which are the feed's data and are not
redistributed; run on a later day, the same command measures a later window. The overnight bars are
licensed data from the vendor's Blue Ocean add-on and are not redistributed either. The night records in
`data/public/` carry every reference value, band, hedge return, opening price and flag, so the
open-based tables can be recomputed from the repository alone; the print-based tables can be recomputed
by a reader holding the same subscription, for the nights the feeds still serve. NAV and holdings files
are the issuers' own downloads and are described by name and date in Appendix A. Model calls are made
with the caller's own API keys through environment variables; no key is stored.

## Author note

The author led the delivery of an institutional ETF servicing platform, creation, redemption and
corporate actions, worked on derivatives processing across options, futures, forwards and swaps, and has
built AI-assisted finance tools independently since 2022. He did not run a trading desk or a
market-making book, and this report does not claim that experience; where market mechanics mattered,
they were checked against public documents rather than asserted from memory, and the result of the
check is cited.

## Declaration on the use of generative AI

A generative AI assistant (Anthropic's Claude) was used throughout this work: to draft and refine the
prototype code and this text, and to act as the news-reading and hedge-proposing models of Findings 6
and 7, alongside two open-weight models run locally. Before posting, the code, the figures and the cited
documents were rechecked with the assistant's help; the recheck corrected the timing of the futures
price paired with each print, the count of traded slots in Frankfurt, and the measurement behind the
emerging-markets result in Finding 7, and the text reports the corrected figures. All factual claims
were verified against the data files the code writes, the issuers' files and the public documents cited,
except as listed in Appendix B, and the author reviewed and edited all content and takes full
responsibility for it. Because generative AI is also part of this report's subject, and because the
assistant's vendor makes two of the four models tested, the safeguard against circularity is structural:
every verdict is graded against market data that no model produced, the opening prices and the traded
prints, by deterministic code; every verdict and its citations are stored verbatim; and every reported
number is written by the published code from the named data sources.

## Appendix A. Facts used, with sources

| Fact | Source |
|---|---|
| Overnight trading expected to start December 6, 2026 on five exchanges (24X, Cboe EDGX, MEMX, Nasdaq, NYSE Arca), each conditional on the consolidated feeds being ready. SEC approval orders: Nasdaq April 10, 2026; Cboe EDGX May 29, 2026; 24X November 27, 2024. NYSE Arca's 22-hour day was approved February 11, 2025 | [4], [5], [8] |
| Overnight session 9pm to 4am ET; one-hour pause from 8pm Monday to Thursday; trades between 9pm and midnight carry the next day's trade date; extended-hours sale condition, not last-sale eligible; closing price set at 4pm | [5], [6] |
| Consolidated feeds to operate 23 hours a day from December 6, 2026 | [4] |
| NSCC clearing from Sunday 8pm to Friday 8pm ET since June 29, 2026 | [19] |
| Overnight price bands: 20% below the lower and above the higher of the official close and the 7:45pm consolidated round-lot sale; each band at least $3.00 from its reference price ($1.00 where the close is under $1.00); sent to the feeds by 8:55pm and disseminated before 9pm; in force to 4am; leveraged ETPs 20% times leverage; temporary, with a replacement to be proposed | [7] |
| SEC order on Nasdaq's 23/5 rule quotes the disclosure that the absence of an updated indicative value is a risk of extended-hours trading | [5] |
| An indicative value every 15 seconds was a listing-rule requirement, removed for most ETFs in 2020; Rule 6c-11 does not require one | [21] |
| ETPs 61% of overnight trading against 21% in core hours | [2] |
| iShares spreads nearly 10 times wider overnight for the most active funds, as much as 30 times for some less frequently traded ones; Blue Ocean data, February 2025 | [3] |
| Blue Ocean session since 2021, 8pm to 4am ET Sunday to Thursday; market makers include Jane Street, Virtu, Flow Traders; demand from retail investors in Asia | [1] |
| A vendor's 24x5 reference price is derived from quote and trade messages in the security across US exchanges, ATSs and OTC venues | [9] |
| Portfolio composition file due to NSCC by 10pm ET on the day before; creation units transact at the NAV next computed after the order | [10], [11] |
| Rule 6c-11: market price is the official closing price, or the bid-ask midpoint when the NAV is calculated; premium and discount history published on that basis | [18] |
| SEC order of February 23, 2026 for a tokenized government money market fund: dealers may transact at $1.00 instead of the next NAV, subject to the application's conditions, among them that a market-based NAV deviation of 0.25% or more suspends that or moves it to the next NAV | [17] |
| Xetra: at least one Designated Sponsor required for continuous trading in each ETF; quoting in at least 80% of effective trading time, measured monthly; maximum spread and minimum quote size set per instrument; mandate ended after six consecutive months below the requirement | [15], [16] |
| Blue Ocean ATS: Form ATS-N of 2021 answers "no" on liquidity-provider arrangements; trading rules of May 2021 describe a 15% price band and no quoting obligation | [22] |
| Nasdaq: a market maker must be willing to buy and sell "on a continuous basis during regular market hours" (Two-Sided Quote Obligation); the order approving 23-hour trading lists market-maker obligations among what will not change, and makes the Market Maker Peg order type unavailable in the night session | [23], [5] |
| Window: 60 nights, evening of August 13 to morning of November 6, 2026, 12 spanning a weekend or holiday; training 434 nights (437 for IBIT) | `grades.json` (`input_facts`), `fits.json` |
| Overnight 5-minute bars, 8pm to 3:59am, Sunday to Thursday sessions; 5,760 slots per fund (60 nights of 96); slots with a trade: SPY 5,719; QQQ 5,689; GLD 5,675; IBIT 5,529; SMH 5,331; TLT 4,873; EWJ 1,086; EEM 319; LQD 131; EWG 28. In quarter-hour slots: EWJ 40.9%; EEM 14.3%; LQD 5.6%; EWG 1.4% | [14]; `grades.json` (`overnight_prints`) |
| Daily opens and closes, two years; 15-minute fund bars with pre- and post-market prints and 5-minute bars for the hedge instruments, about sixty trading days; hourly bars for ES, NQ, NIY, ZB, ZN, GC futures, BTC-USD, JPY=X, EURUSD=X and the cash indices, two years; 15-minute Xetra bars, about sixty trading days; all as downloaded November 9, 2026 | [20] |
| Official NAV files: iShares Data Download, 'Historical' sheet with NAV per share, ex-dividends and non-fair-valued NAV, for EWJ, EWG, EEM, TLT, LQD, IBIT; State Street NAV History for SPY and GLD; all to November 6, 2026 | [12], [13] |
| 4pm close against official NAV over the 60 test nights, median absolute difference, bps: SPY 2.0; TLT 3.9; LQD 4.5; EWG 9.5; IBIT 11.9; EWJ 18.4; EEM 18.7; GLD 46.8 (maximum 240) | `grades.json` (`input_facts`) |
| Fair-value adjustment, official against non-fair-valued NAV, median absolute and maximum, bps: EWJ 52.5 / 451 (November 5); EEM 58.9 / 412 (November 5); EWG 29.0 / 96 (September 16). SPY closed 4.4% lower on November 5 | `grades.json` (`input_facts`); `nights_SPY.json` |
| Ex-dividend mornings in the window, bps of the prior close: SPY September 18 (24.8); QQQ September 21 (10.4); TLT September 1, October 1, November 2 (38.1, 40.1, 41.9); LQD September 1, October 1, November 2 (41.8, 42.9, 38.4). The feed lacked the two November 2 ex-dates | `grades.json` (`input_facts`); NAV files; [20] |
| Betas and training R-squared: SPY 0.92/0.90; QQQ 0.93/0.92; SMH 1.62/0.78; EWJ 0.77/0.78; EWG 0.88/0.55; EEM 1.10/0.39; TLT 1.15/0.86; LQD 1.09/0.67; GLD 0.96/0.93; IBIT 1.01/0.95 | `fits.json` |
| Mean absolute error against the 9:30 open, all grid hours, flat carry vs reference, bps: SPY 36/26; QQQ 67/44; SMH 158/117; EWJ 75/70; EWG 63/57; EEM 99/89; TLT 41/37; LQD 24/22; GLD 97/73; IBIT 140/101. The same reference started from the 4pm close: EWJ 65.8; EWG 55.4; EEM 88.2; IBIT 98.7; SPY 26.3. Open-band coverage: SPY .951; QQQ .918; SMH .888; EWJ .893; EWG .938; EEM .873; TLT .893; LQD .882; GLD .836; IBIT .907 | `grades.json` |
| Same-instant traded bars against the close-anchored reference: count, median and 90th percentile distance in bps, mean premium: SPY 4,572, 2.4/5.8/+1.5; QQQ 4,542, 3.3/8.9/+1.4; GLD 4,570, 2.6/7.3/+2.0; IBIT 3,838, 3.6/7.4/-1.3; TLT 3,951, 4.9/15.8/-2.4; SMH 4,263, 22.7/73.1/+5.4; EWJ 855, 41.3/86.3/-10.4; EEM 262, 62.2/139.7/-19.9; LQD 113, 6.2/24.4/-3.6; EWG 23, 44.3/224.7/-32.3. Against the NAV-anchored reference, median: SPY 3.7; IBIT 10.9; EWJ 45.1. SPY by hour, 8pm to 3am: 2.2, 2.4, 2.4, 2.4, 2.3, 2.4, 2.4, 2.7 | `grades.json` (`overnight_prints.same_instant`, `.same_instant_nav_anchor`, `.by_hour`) |
| Traded bars left out of the distances because their futures price was older than the print (hourly bars only), with their median distance: SPY 1,099, 3.7; QQQ 1,099, 7.3; GLD 1,057, 10.6; IBIT 1,691, 14.8; TLT 881, 5.0; SMH 1,020, 30.1; EWJ 203, 31.6; EEM 52, 45.1; LQD 17, 5.4; EWG 5, 58.7 | `grades.json` (`overnight_prints.lagged_reference`) |
| Correlation between the last same-instant traded print's deviation (2am to 4am) and the open's deviation, both from the close-anchored reference, with nights: EEM 0.87 (33); EWJ 0.61 (51); SMH 0.61 (60); QQQ 0.27 (60); GLD 0.24 (60); SPY 0.20 (60); TLT 0.00 (58); IBIT -0.21 (60); LQD -0.22 (18); EWG 5 nights | `grades.json` (`overnight_prints.late_print_vs_open`) |
| Emerging markets, 25 nights with a late print and all four Asian sessions: correlation of the print's deviation with the sessions' fitted contribution 0.72; median absolute deviation 60.8 bps, 34.5 after removing the contribution; mean -22.6, then -5.1 | `hedge_proposals.json` (`late_prints_vs_added_instruments`) |
| Open band half-width for SPY, 8pm and 4am: 78.5 and 63.1 bps. Share of same-instant traded bars outside the open band: 0 for SPY, QQQ, GLD, IBIT, TLT, SMH; EWJ 4.6%; EEM 2.7%; LQD 1.8%; EWG 17% | `grades.json` |
| Trading band from the first 30 test nights applied to the last 30; half-width in bps, coverage, prints: SPY 5.8 / .887 of 2,818; QQQ 6.6 / .710 of 2,823; GLD 6.4 / .827 of 2,809; IBIT 8.7 / .937 of 2,744; TLT 13.9 / .870 of 2,616; SMH 52.7 / .765 of 2,714; EWJ 83.7 / .892 of 547; EEM 98.3 / .599 of 182; LQD and EWG not calibrated (44 and 7 prints). Median distance, first 30 nights then last 30: QQQ 2.6, 3.8; SMH 18.3, 25.2; GLD 2.5, 2.7; SPY 2.4, 2.4 | `grades.json` (`overnight_prints.trading_band`); `nights_*.json` |
| Closest approach of any opening price to its static band: 13.5 percentage points (SMH) | `grades.json` (`input_facts.static_band_min_room_bps`) |
| Evidence layer, first stage: Claude Haiku 5.5, flag-only prompt, six equity funds, 60 nights at 1am and 4am, 720 readings, 148 flags, about 9.4M input tokens; news items over 60 nights for the ten largest holdings: SMH 15,054; SPY 20,484; QQQ 22,729; EWJ 648; EWG 302; EEM 633. Sony flag on the night of November 5: open 168 bps below the 4am reference | `evidence_*.json`, `evidence_grades.json`, `nights_EWJ.json` |
| Evidence layer, second stage, on the 148 flags plus a deterministic sample of 50 quiet readings (26 events in the 198). Claude Sonnet 5.5: 198 answered, 2 not parseable; kept 56 flags (7 events), declined 92 (13 events); quiet sample 0 of 50 (6 events); direction right 37 of 52 | `evidence_grades.json` (`_second_stage`) |
| Local models on the same 198 readings. Qwen 2B distill with reasoning: 186 answered, 12 prompts over its 40,960-token context, 11 answers not parseable after two retries; 46 flags, 5 citing unknown ids; kept 34 (9 events), declined 105 (11 events); 12 flags in 47 quiet readings; direction right 21 of 43. Qwen3.5 9B without reasoning (request-level reasoning_effort "none"; with reasoning it spent 7,865 tokens on one prompt and gave no answer): 193 answered, 5 prompts over its 48,000-token context, none unparseable; 8 flags, all on first-stage flags (1 event), declined 138 (19 events), 0 of 47 quiet; direction right 7 of 8 | `evidence_grades.json` (`_second_stage`), `evidence_*.json` |
| Hedge proposer: Claude Sonnet 5.5, one call per fund, universe of 34 instruments, no unknown symbols. Out-of-sample R-squared, hand-picked vs proposal with fitted weights vs proposal with the model's weights: SPY .977/.981/.977; EWG .550/.865/.875 (^GDAXI .7, ES=F .25, EURUSD=X 1.0; error 37.5 to 22.8 bps); LQD .740/.839/.805 (ZN=F .75, ZB=F .2, ES=F .06; error 11.7 to 9.4 bps); QQQ .975, SMH .771, EWJ .636, TLT .884, IBIT .974 unchanged; GLD .951 unchanged with SI=F .05 and EURUSD=X .04 added | `hedge_proposals.json` |
| Emerging markets proposal (^HSI .32, ^TWII .25, ^KS11 .18, ^BSESN .15), 47 nights with all four: S&P futures alone .459 (.429 on all 60); proposal measured previous close to latest close .165, with S&P futures .512; measured over the indices' own sessions .369 (.397 with the model's weights), with S&P futures .619, error 71.8 to 57.8 bps. Training fit prefers the session measurement for these four and the previous-close measurement for ^GDAXI | `hedge_proposals.json` |
| Frankfurt control: 15-minute Xetra bars for SXR8, IUSA, VUSA, EQQQ, SPYL, D5BM, LYPS, H4ZF, ZPRR; 49 sessions September 1 to November 9, 2026; 1,254 quarter-hour slots per fund from 9:00 Frankfurt time to the US open; reference = previous last trade less any ex-dividend, times futures return (ES=F, NQ=F or RTY=F), divided by the EUR/USD change; traded bars only; band from the first 24 sessions applied to the last 25; plain rule vs fitted, out-of-sample R-squared: SXR8 .991 vs .974; IUSA .970 vs .961; VUSA .987 vs .965; EQQQ .981 vs .960; SPYL .989 vs .973; D5BM .979 vs .949; LYPS .977 vs .958; H4ZF .967 vs .951; ZPRR .983 vs .955 | `frankfurt.json`, [20] |

## Appendix B. What was not verified

- The 0.25% condition in [17] is taken from summaries of the notice of application; the order itself
  grants the relief "subject to the conditions contained in the application" and does not state the
  figure.
- That the SEC's Nasdaq order asks nobody to supply an indicative value rests on a text search of the
  order, not a full reading.
- NYSE's 61% and 21% are quoted as the research note gives them; the note does not say in that sentence
  whether they are shares of volume or of notional.
- Blue Ocean's present market-maker arrangements: only the 2021 filing and rules were read. Its share of
  overnight volume was not verified; secondary summaries of a 2024 regulatory settlement put it at
  about 95%.
- The approval status of NYSE Arca's and MEMX's overnight sessions is taken from [4]; their individual
  filings were not read. Market-maker obligations at night were checked for Nasdaq only.
- The issuers' fair-value policies were not read; the size of the adjustment is measured from the
  issuers' own two NAV columns.
- The mapping from foreign holdings to US news tickers was built by hand for the largest fifteen holdings
  of three funds and checked by name; it is in the repository.

## References

1. Schmerken, I. *Overnight Trading Gains Traction with the NYSE on Board.* FlexTrade, November 21, 2024. flextrade.com/resources.
2. Poser, S. W. *Night Moves: What Trades and When in the Overnight Market.* NYSE Research, June 2025. nyse.com/data-insights.
3. BlackRock. *Market Spotlight: 24 Hour Trading.* 2025. blackrock.com/corporate/literature/whitepaper.
4. WilmerHale. *23x5 Trading Comes to US Exchanges: What Firms Should Know Before Launch*, September 29, 2026.
5. Securities and Exchange Commission. Release No. 34-105199, April 10, 2026, order granting accelerated approval of SR-Nasdaq-2025-109 (Nasdaq trading 23 hours a day, five days a week); Release No. 34-105587, May 29, 2026 (Cboe EDGX); Release No. 34-101777, November 27, 2024 (24X National Exchange); Release No. 34-102400, February 11, 2025 (NYSE Arca).
6. New York Stock Exchange. *Extended-Hours Trading FAQs*, version 4.0, August 2026. nyse.com/publicdocs.
7. Securities and Exchange Commission. Release No. 34-106042, August 5, 2026, File No. 4-631, order approving the Twenty-Seventh Amendment to the Limit Up-Limit Down Plan (temporary price band protections in overnight trading); notice of filing, Release No. 34-105596, June 1, 2026; plan text at luldplan.com.
8. Gerber, M. S. and Kim, C. S. *NYSE Arca and Nasdaq to Launch Extended Trading: What Companies Should Consider.* Harvard Law School Forum on Corporate Governance, October 21, 2026.
9. Tiingo. *24x5 Real-time Stock Data API: Consolidated US Equities.* tiingo.com/products.
10. DTCC Learning Center. *ETF Timeline and Submission Processing.* dtcclearning.com.
11. 17 CFR 270.22c-1 (Rule 22c-1, pricing of redeemable securities).
12. BlackRock iShares. Fund pages for EWJ, EWG, EEM, TLT, LQD and IBIT, "Data Download" files (Historical, Holdings, Distributions sheets), as of November 6, 2026. ishares.com.
13. State Street Global Advisors. SPY and GLD fund pages, "Most Recent NAV / NAV History" files, as of November 6, 2026; SPDR Gold Trust prospectus. ssga.com.
14. Blue Ocean ATS overnight session data, 5-minute bars, via Tiingo's BOATS add-on (api.tiingo.com/boats). Licensed; not redistributed.
15. Deutsche Börse. *Designated Sponsor Guide*, November 10, 2025. cashmarket.deutsche-boerse.com.
16. Deutsche Börse / Xetra. *Liquidity through Designated Sponsors.* eurexgroup.com/xetra-en/trading/trading-models.
17. Securities and Exchange Commission. Investment Company Act Release No. 35968, February 23, 2026, WisdomTree Digital Trust et al., File No. 812-15788; notice of application, 91 FR 3757, January 28, 2026; Ropes & Gray, *Investment Management Update, March to April 2026*.
18. 17 CFR 270.6c-11 (Rule 6c-11), including the definition of market price and the website disclosure conditions.
19. DTCC. Press release of June 29, 2026 on NSCC's 24x5 clearing hours. dtcc.com/press-releases/2026.
20. Yahoo Finance chart feed (query1.finance.yahoo.com/v8/finance/chart), daily, hourly, 15-minute and 5-minute bars and dividend events, retrieved November 7 to 9, 2026.
21. Securities and Exchange Commission. Release No. 34-88558, April 2020, SR-CboeBZX-2020-007 (removal of the intraday indicative value requirement from the exchange's ETF listing rules); K&L Gates, *New Listing Rules Adopted for ETFs Relying on Rule 6c-11*, May 5, 2020.
22. Blue Ocean ATS, LLC. Form ATS-N, effective June 1, 2021 (SEC EDGAR, CIK 1795131); *BOATS Trading Rules*, May 2021.
23. The Nasdaq Stock Market LLC. Rules, Equity 2, Section 5(a)(1), Two-Sided Quote Obligation; text as set out in Exhibit 5 to SR-NASDAQ-2025-101.
