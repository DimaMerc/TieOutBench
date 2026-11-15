# Overnight reference value — backtest summary

Generated 2026-11-15T14:00. All inputs are real market data; see the footnotes for proxies. The reference value is the 4pm NAV moved by the fund's hedge instrument (and currency) since 4pm, with an overnight beta estimated on nights before the test window. The band is nominally 90%. Truth is the next morning's 9:30 opening price.

## By fund

| Fund | Kind | Hedge | Train nights | Test nights | Beta | R2 train | Resid train (bps) | Resid test (bps) | MAE naive (bps) | MAE ref (bps) | Coverage Gaussian | Coverage empirical | Usable | Nights > 100 bps | Static band ever binding |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY | A | ES=F | 434 | 60 | 0.925 | 0.90 | 21.4 | 6.9 | 35.9 | 26.4 | 0.957 | 0.951 | 0.99 | 3 | no |
| QQQ | A | NQ=F | 434 | 60 | 0.931 | 0.92 | 25.4 | 13.5 | 67.1 | 43.8 | 0.897 | 0.918 | 0.99 | 13 | no |
| SMH | A | NQ=F | 434 | 60 | 1.625 | 0.78 | 80.0 | 97.4 | 158.1 | 117.3 | 0.856 | 0.888 | 0.99 | 38 | no |
| EWJ | B | NIY=F | 434 | 60 | 0.765 | 0.78 | 55.3 | 66.6 | 74.9 | 70.2 | 0.931 | 0.893 | 0.99 | 15 | no |
| EWG | B | ES=F | 434 | 60 | 0.876 | 0.55 | 65.5 | 56.0 | 62.9 | 57.1 | 0.933 | 0.938 | 0.99 | 9 | no |
| EEM | B | ES=F | 434 | 60 | 1.102 | 0.39 | 94.6 | 96.3 | 99.0 | 89.3 | 0.893 | 0.873 | 0.99 | 25 | no |
| TLT | A | ZB=F | 434 | 60 | 1.155 | 0.86 | 20.4 | 19.0 | 40.9 | 36.6 | 0.815 | 0.893 | 0.99 | 3 | no |
| LQD | A | ZN=F | 434 | 60 | 1.093 | 0.67 | 17.5 | 15.6 | 24.3 | 21.7 | 0.822 | 0.882 | 0.99 | 0 | no |
| GLD | A | GC=F | 434 | 60 | 0.961 | 0.93 | 32.6 | 27.6 | 96.6 | 73.4 | 0.893 | 0.836 | 0.99 | 25 | no |
| IBIT | C | BTC-USD | 437 | 60 | 1.012 | 0.95 | 47.3 | 32.0 | 140.3 | 100.7 | 0.924 | 0.907 | 1.00 | 31 | no |

Reading the table: *MAE naive* is the error of carrying the 4pm NAV flat through the night; *MAE ref* is the error of the hedge-moved reference value, averaged over all grid hours; both are against the 9:30 open. Two bands are scored, both nominally 90%: the *Gaussian* band (residual spread plus the hedge's remaining hourly variance) and the *empirical* band (for each hour, the 90th percentile of the carry-forward's own error on the training nights). Coverage should sit near 0.90; far above it the band is too wide to be useful, far below it the band lies. *Resid test* against *Resid train* shows whether the test window was calmer or wilder than the fit. *Static band ever binding* asks whether the exchanges' 20% band would have excluded a single opening price in the window.

## Overnight trades against the reference value

| Fund | 5-minute slots | Slots with a trade | Share | Share of 15-minute slots | Same-instant traded bars | Mean premium (bps) | Median abs (bps) | p90 abs (bps) | Outside the open band | Last print vs open: corr (nights) |
|---|---|---|---|---|---|---|---|---|---|---|
| SPY | 5760 | 5719 | 99.3% | 99.4% | 4572 | 1.5 | 2.4 | 5.8 | 0.0000 | 0.20 (60) |
| QQQ | 5760 | 5689 | 98.8% | 98.9% | 4542 | 1.4 | 3.3 | 8.9 | 0.0000 | 0.27 (60) |
| SMH | 5760 | 5331 | 92.6% | 98.5% | 4263 | 5.4 | 22.7 | 73.1 | 0.0000 | 0.61 (60) |
| EWJ | 5760 | 1086 | 18.9% | 40.9% | 855 | -10.4 | 41.3 | 86.3 | 0.0456 | 0.61 (51) |
| EWG | 5760 | 28 | 0.5% | 1.4% | 23 | -32.3 | 44.3 | 224.7 | 0.1739 | -0.27 (5) |
| EEM | 5760 | 319 | 5.5% | 14.3% | 262 | -19.9 | 62.2 | 139.7 | 0.0267 | 0.87 (33) |
| TLT | 5760 | 4873 | 84.6% | 95.4% | 3951 | -2.4 | 4.9 | 15.8 | 0.0000 | -0.00 (58) |
| LQD | 5760 | 131 | 2.3% | 5.6% | 113 | -3.6 | 6.2 | 24.4 | 0.0177 | -0.22 (18) |
| GLD | 5760 | 5675 | 98.5% | 99.4% | 4570 | 2.0 | 2.6 | 7.3 | 0.0000 | 0.24 (60) |
| IBIT | 5760 | 5529 | 96.0% | 99.3% | 3838 | -1.3 | 3.6 | 7.4 | 0.0000 | -0.21 (60) |

A slot is five minutes of the 8pm to 4am session, 96 a night; a slot counts as traded when the bar shows volume (the feed repeats the last price through quiet slots, and returns no bar before a session's first trade). Distances are measured on *same-instant* bars: traded bars whose futures price is the close of the 5-minute futures bar covering the same five minutes. The public feed serves about sixty trading days of 5-minute bars; on earlier nights only a bar ending on the hour, where the hourly futures bar closes at the same instant, qualifies. A positive mean is a premium to the reference, a negative one a discount. 'Outside the open band' is the share of those bars beyond the open band for that hour. The last column asks whether the last trade before 4am says where the fund will open: the correlation, across nights, between that print's deviation and the open's deviation, both from the close-anchored reference.

## SPY — SPDR S&P 500 ETF Trust

Kind A, hedge ES=F, beta 0.925. NAV source: file. Overnight tape: tiingo_boats.

| Hour (ET) | n | MAE ref (bps) | Median ref (bps) | MAE naive (bps) | Coverage Gaussian | Half-band Gaussian (bps) | Coverage empirical | Half-band empirical (bps) | Usable share |
|---|---|---|---|---|---|---|---|---|---|
| 20:00 | 59 | 28.8 | 19.1 | 36.0 | 0.966 | 82.7 | 0.949 | 78.5 | 1.00 |
| 21:00 | 59 | 28.5 | 17.6 | 36.0 | 0.966 | 80.0 | 0.966 | 76.1 | 1.00 |
| 22:00 | 59 | 28.4 | 20.4 | 36.0 | 0.983 | 77.3 | 0.932 | 73.2 | 1.00 |
| 23:00 | 59 | 28.4 | 20.7 | 36.0 | 0.966 | 74.5 | 0.966 | 73.7 | 1.00 |
| 00:00 | 59 | 26.7 | 17.6 | 36.0 | 0.966 | 71.5 | 0.966 | 77.1 | 1.00 |
| 01:00 | 60 | 26.8 | 21.0 | 35.7 | 0.950 | 68.4 | 0.950 | 71.0 | 1.00 |
| 02:00 | 60 | 25.2 | 16.8 | 35.7 | 0.917 | 65.2 | 0.933 | 69.8 | 1.00 |
| 03:00 | 60 | 24.0 | 16.2 | 35.7 | 0.933 | 61.8 | 0.933 | 62.5 | 1.00 |
| 04:00 | 60 | 21.2 | 17.5 | 35.7 | 0.967 | 58.2 | 0.967 | 63.1 | 1.00 |

Overnight prints (Blue Ocean, 5-minute bars): 5719 of 5760 slots traded on 60 nights. Same-instant traded bars against the close-anchored reference: 4572 bars, mean premium 1.5 bps, median absolute 2.4 bps, 90th percentile 5.8 bps; against the NAV-anchored reference, median absolute 3.7 bps. Traded bars left out because their futures price was up to 55 minutes older than the print (hourly bars only): 1099, median absolute 3.7 bps.

| Hour (ET) | same-instant traded bars | mean premium (bps) | median abs (bps) |
|---|---|---|---|
| 20 | 575 | 1.5 | 2.2 |
| 21 | 574 | 1.4 | 2.4 |
| 22 | 575 | 1.4 | 2.4 |
| 23 | 569 | 1.4 | 2.4 |
| 00 | 537 | 1.5 | 2.3 |
| 01 | 575 | 1.5 | 2.4 |
| 02 | 580 | 1.5 | 2.4 |
| 03 | 587 | 1.5 | 2.7 |

Trading band, calibrated on same-instant traded prints 2026-08-13 to 2026-09-24 (1754 prints; 90th percentile 5.6 bps, median 2.4 bps) and applied to 2026-09-25 to 2026-11-05: covered 0.887 of 2818 prints; mean half-width 5.8 bps against 71.7 bps for the open band at the same hours.

## QQQ — Invesco QQQ Trust

Kind A, hedge NQ=F, beta 0.931. NAV source: proxy_close. Overnight tape: tiingo_boats.

| Hour (ET) | n | MAE ref (bps) | Median ref (bps) | MAE naive (bps) | Coverage Gaussian | Half-band Gaussian (bps) | Coverage empirical | Half-band empirical (bps) | Usable share |
|---|---|---|---|---|---|---|---|---|---|
| 20:00 | 59 | 51.8 | 45.4 | 67.4 | 0.898 | 107.0 | 0.915 | 117.4 | 1.00 |
| 21:00 | 59 | 50.0 | 43.2 | 67.4 | 0.932 | 103.4 | 0.949 | 114.5 | 1.00 |
| 22:00 | 59 | 47.7 | 39.5 | 67.4 | 0.898 | 99.8 | 0.898 | 99.2 | 1.00 |
| 23:00 | 59 | 48.3 | 44.8 | 67.4 | 0.898 | 96.0 | 0.915 | 101.8 | 1.00 |
| 00:00 | 59 | 43.6 | 38.6 | 67.4 | 0.898 | 92.0 | 0.915 | 98.4 | 1.00 |
| 01:00 | 60 | 42.2 | 32.5 | 66.7 | 0.867 | 87.8 | 0.900 | 94.4 | 1.00 |
| 02:00 | 60 | 40.3 | 29.5 | 66.7 | 0.883 | 83.5 | 0.900 | 89.5 | 1.00 |
| 03:00 | 60 | 38.3 | 29.5 | 66.7 | 0.900 | 78.9 | 0.900 | 85.6 | 1.00 |
| 04:00 | 60 | 32.7 | 27.8 | 66.7 | 0.900 | 74.0 | 0.967 | 82.1 | 1.00 |

Overnight prints (Blue Ocean, 5-minute bars): 5689 of 5760 slots traded on 60 nights. Same-instant traded bars against the close-anchored reference: 4542 bars, mean premium 1.4 bps, median absolute 3.3 bps, 90th percentile 8.9 bps; against the NAV-anchored reference, median absolute 3.3 bps. Traded bars left out because their futures price was up to 55 minutes older than the print (hourly bars only): 1099, median absolute 7.3 bps.

| Hour (ET) | same-instant traded bars | mean premium (bps) | median abs (bps) |
|---|---|---|---|
| 20 | 563 | 1.5 | 2.8 |
| 21 | 562 | 1.4 | 3.0 |
| 22 | 562 | 1.2 | 3.4 |
| 23 | 573 | 1.2 | 3.5 |
| 00 | 538 | 1.5 | 3.4 |
| 01 | 576 | 1.5 | 3.1 |
| 02 | 580 | 1.4 | 3.7 |
| 03 | 588 | 1.7 | 4.0 |

Trading band, calibrated on same-instant traded prints 2026-08-13 to 2026-09-24 (1719 prints; 90th percentile 6.8 bps, median 2.6 bps) and applied to 2026-09-25 to 2026-11-05: covered 0.710 of 2823 prints; mean half-width 6.6 bps against 98.1 bps for the open band at the same hours.

## SMH — VanEck Semiconductor ETF

Kind A, hedge NQ=F, beta 1.625. NAV source: proxy_close. Overnight tape: tiingo_boats.

| Hour (ET) | n | MAE ref (bps) | Median ref (bps) | MAE naive (bps) | Coverage Gaussian | Half-band Gaussian (bps) | Coverage empirical | Half-band empirical (bps) | Usable share |
|---|---|---|---|---|---|---|---|---|---|
| 20:00 | 59 | 127.6 | 123.5 | 157.7 | 0.881 | 216.5 | 0.915 | 248.7 | 1.00 |
| 21:00 | 59 | 124.2 | 114.3 | 157.7 | 0.915 | 211.2 | 0.915 | 244.0 | 1.00 |
| 22:00 | 59 | 122.0 | 96.6 | 157.7 | 0.898 | 205.7 | 0.915 | 225.8 | 1.00 |
| 23:00 | 59 | 123.5 | 106.4 | 157.7 | 0.864 | 200.1 | 0.915 | 228.6 | 1.00 |
| 00:00 | 59 | 117.7 | 104.1 | 157.7 | 0.864 | 194.4 | 0.915 | 234.5 | 1.00 |
| 01:00 | 60 | 117.1 | 95.8 | 158.5 | 0.833 | 188.4 | 0.833 | 212.9 | 1.00 |
| 02:00 | 60 | 113.4 | 95.4 | 158.5 | 0.833 | 182.3 | 0.883 | 203.3 | 1.00 |
| 03:00 | 60 | 109.1 | 103.1 | 158.5 | 0.800 | 176.0 | 0.867 | 199.3 | 1.00 |
| 04:00 | 60 | 101.7 | 80.4 | 158.5 | 0.817 | 169.4 | 0.833 | 179.6 | 1.00 |

Overnight prints (Blue Ocean, 5-minute bars): 5331 of 5760 slots traded on 60 nights. Same-instant traded bars against the close-anchored reference: 4263 bars, mean premium 5.4 bps, median absolute 22.7 bps, 90th percentile 73.1 bps; against the NAV-anchored reference, median absolute 22.7 bps. Traded bars left out because their futures price was up to 55 minutes older than the print (hourly bars only): 1020, median absolute 30.1 bps.

| Hour (ET) | same-instant traded bars | mean premium (bps) | median abs (bps) |
|---|---|---|---|
| 20 | 537 | 6.7 | 18.6 |
| 21 | 540 | 6.5 | 17.2 |
| 22 | 538 | 2.9 | 20.0 |
| 23 | 526 | 2.9 | 18.7 |
| 00 | 493 | 4.6 | 19.2 |
| 01 | 532 | 4.5 | 24.1 |
| 02 | 547 | 6.8 | 32.9 |
| 03 | 550 | 8.0 | 35.8 |

Trading band, calibrated on same-instant traded prints 2026-08-13 to 2026-09-24 (1549 prints; 90th percentile 55.6 bps, median 18.3 bps) and applied to 2026-09-25 to 2026-11-05: covered 0.765 of 2714 prints; mean half-width 52.7 bps against 219.6 bps for the open band at the same hours.

## EWJ — iShares MSCI Japan ETF

Kind B, hedge NIY=F, beta 0.765, currency gamma 0.835. NAV source: file. Overnight tape: tiingo_boats.

| Hour (ET) | n | MAE ref (bps) | Median ref (bps) | MAE naive (bps) | Coverage Gaussian | Half-band Gaussian (bps) | Coverage empirical | Half-band empirical (bps) | Usable share |
|---|---|---|---|---|---|---|---|---|---|
| 20:00 | 58 | 78.1 | 66.6 | 75.7 | 0.948 | 181.3 | 0.862 | 149.2 | 1.00 |
| 21:00 | 59 | 79.4 | 65.2 | 75.1 | 0.898 | 176.0 | 0.881 | 151.2 | 1.00 |
| 22:00 | 59 | 74.7 | 57.1 | 75.1 | 0.932 | 170.5 | 0.881 | 149.9 | 1.00 |
| 23:00 | 59 | 73.2 | 57.2 | 75.1 | 0.932 | 164.9 | 0.898 | 144.3 | 1.00 |
| 00:00 | 59 | 69.5 | 58.7 | 75.1 | 0.949 | 159.1 | 0.932 | 144.5 | 1.00 |
| 01:00 | 60 | 68.7 | 59.9 | 74.6 | 0.917 | 153.0 | 0.883 | 136.7 | 1.00 |
| 02:00 | 60 | 65.3 | 59.3 | 74.6 | 0.950 | 146.7 | 0.917 | 136.9 | 1.00 |
| 03:00 | 60 | 61.8 | 48.9 | 74.6 | 0.917 | 140.1 | 0.883 | 126.8 | 1.00 |
| 04:00 | 60 | 61.4 | 51.4 | 74.6 | 0.933 | 133.2 | 0.900 | 123.2 | 1.00 |

Overnight prints (Blue Ocean, 5-minute bars): 1086 of 5760 slots traded on 59 nights. Same-instant traded bars against the close-anchored reference: 855 bars, mean premium -10.4 bps, median absolute 41.3 bps, 90th percentile 86.3 bps; against the NAV-anchored reference, median absolute 45.1 bps. Traded bars left out because their futures price was up to 55 minutes older than the print (hourly bars only): 203, median absolute 31.6 bps.

| Hour (ET) | same-instant traded bars | mean premium (bps) | median abs (bps) |
|---|---|---|---|
| 20 | 177 | -1.5 | 29.2 |
| 21 | 157 | -14.9 | 46.7 |
| 22 | 93 | -14.3 | 41.3 |
| 23 | 83 | -10.0 | 48.8 |
| 00 | 69 | -7.8 | 51.7 |
| 01 | 87 | -12.0 | 46.6 |
| 02 | 107 | -14.4 | 40.4 |
| 03 | 82 | -12.4 | 44.7 |

Trading band, calibrated on same-instant traded prints 2026-08-13 to 2026-09-24 (308 prints; 90th percentile 86.4 bps, median 43.9 bps) and applied to 2026-09-25 to 2026-11-05: covered 0.892 of 547 prints; mean half-width 83.7 bps against 140.3 bps for the open band at the same hours.

## EWG — iShares MSCI Germany ETF

Kind B, hedge ES=F, beta 0.876, currency gamma 1.148. NAV source: file. Overnight tape: tiingo_boats.

| Hour (ET) | n | MAE ref (bps) | Median ref (bps) | MAE naive (bps) | Coverage Gaussian | Half-band Gaussian (bps) | Coverage empirical | Half-band empirical (bps) | Usable share |
|---|---|---|---|---|---|---|---|---|---|
| 20:00 | 58 | 60.4 | 46.8 | 62.7 | 0.948 | 128.9 | 0.948 | 138.6 | 1.00 |
| 21:00 | 59 | 60.6 | 46.2 | 63.2 | 0.949 | 127.4 | 0.949 | 143.2 | 1.00 |
| 22:00 | 59 | 60.0 | 45.2 | 63.2 | 0.932 | 125.9 | 0.949 | 142.2 | 1.00 |
| 23:00 | 59 | 59.1 | 42.6 | 63.2 | 0.932 | 124.3 | 0.932 | 133.0 | 1.00 |
| 00:00 | 59 | 57.9 | 42.9 | 63.2 | 0.932 | 122.8 | 0.932 | 140.1 | 1.00 |
| 01:00 | 60 | 56.4 | 42.5 | 62.5 | 0.917 | 121.2 | 0.933 | 132.6 | 1.00 |
| 02:00 | 60 | 56.2 | 42.0 | 62.5 | 0.917 | 119.6 | 0.933 | 129.2 | 1.00 |
| 03:00 | 60 | 53.2 | 42.7 | 62.5 | 0.917 | 118.0 | 0.917 | 132.7 | 1.00 |
| 04:00 | 60 | 50.2 | 39.4 | 62.5 | 0.950 | 116.3 | 0.950 | 123.2 | 1.00 |

Overnight prints (Blue Ocean, 5-minute bars): 28 of 5760 slots traded on 18 nights. Same-instant traded bars against the close-anchored reference: 23 bars, mean premium -32.3 bps, median absolute 44.3 bps, 90th percentile 224.7 bps; against the NAV-anchored reference, median absolute 39.8 bps. Traded bars left out because their futures price was up to 55 minutes older than the print (hourly bars only): 5, median absolute 58.7 bps.

| Hour (ET) | same-instant traded bars | mean premium (bps) | median abs (bps) |
|---|---|---|---|
| 20 | 3 | -46.8 | 230.4 |
| 21 | 4 | -28.7 | 34.8 |
| 22 | 1 | -15.6 | 15.6 |
| 23 | 2 | 2.9 | 14.3 |
| 00 | 3 | -8.9 | 51.6 |
| 01 | 5 | -77.3 | 21.3 |
| 02 | 3 | -22.1 | 26.7 |
| 03 | 2 | 1.4 | 69.1 |

Trading band: not calibrated, only 7 same-instant traded prints in the calibration half (50 needed).

## EEM — iShares MSCI Emerging Markets ETF

Kind B, hedge ES=F, beta 1.102. NAV source: file. Overnight tape: tiingo_boats.

| Hour (ET) | n | MAE ref (bps) | Median ref (bps) | MAE naive (bps) | Coverage Gaussian | Half-band Gaussian (bps) | Coverage empirical | Half-band empirical (bps) | Usable share |
|---|---|---|---|---|---|---|---|---|---|
| 20:00 | 59 | 92.1 | 79.8 | 99.0 | 0.881 | 179.3 | 0.881 | 174.5 | 1.00 |
| 21:00 | 59 | 91.2 | 78.0 | 99.0 | 0.915 | 177.6 | 0.881 | 169.4 | 1.00 |
| 22:00 | 59 | 91.9 | 76.9 | 99.0 | 0.864 | 175.9 | 0.847 | 164.8 | 1.00 |
| 23:00 | 59 | 90.7 | 77.3 | 99.0 | 0.898 | 174.1 | 0.864 | 169.3 | 1.00 |
| 00:00 | 59 | 89.3 | 75.2 | 99.0 | 0.898 | 172.4 | 0.898 | 169.7 | 1.00 |
| 01:00 | 60 | 89.9 | 77.8 | 99.0 | 0.900 | 170.6 | 0.867 | 163.2 | 1.00 |
| 02:00 | 60 | 89.7 | 83.6 | 99.0 | 0.883 | 168.8 | 0.867 | 162.8 | 1.00 |
| 03:00 | 60 | 86.0 | 78.2 | 99.0 | 0.900 | 166.9 | 0.850 | 155.3 | 1.00 |
| 04:00 | 60 | 83.5 | 68.3 | 99.0 | 0.900 | 165.1 | 0.900 | 156.6 | 1.00 |

Overnight prints (Blue Ocean, 5-minute bars): 319 of 5760 slots traded on 56 nights. Same-instant traded bars against the close-anchored reference: 262 bars, mean premium -19.9 bps, median absolute 62.2 bps, 90th percentile 139.7 bps; against the NAV-anchored reference, median absolute 62.6 bps. Traded bars left out because their futures price was up to 55 minutes older than the print (hourly bars only): 52, median absolute 45.1 bps.

| Hour (ET) | same-instant traded bars | mean premium (bps) | median abs (bps) |
|---|---|---|---|
| 20 | 47 | -18.9 | 46.8 |
| 21 | 44 | -7.6 | 55.5 |
| 22 | 34 | -30.7 | 66.7 |
| 23 | 21 | -54.8 | 77.4 |
| 00 | 8 | -55.1 | 97.1 |
| 01 | 34 | -0.3 | 55.2 |
| 02 | 48 | -23.7 | 57.4 |
| 03 | 26 | -7.8 | 96.3 |

Trading band, calibrated on same-instant traded prints 2026-08-13 to 2026-09-24 (80 prints; 90th percentile 98.3 bps, median 37.2 bps) and applied to 2026-09-25 to 2026-11-05: covered 0.599 of 182 prints; mean half-width 98.3 bps against 165.1 bps for the open band at the same hours.

## TLT — iShares 20+ Year Treasury Bond ETF

Kind A, hedge ZB=F, beta 1.155. NAV source: file. Overnight tape: tiingo_boats.

| Hour (ET) | n | MAE ref (bps) | Median ref (bps) | MAE naive (bps) | Coverage Gaussian | Half-band Gaussian (bps) | Coverage empirical | Half-band empirical (bps) | Usable share |
|---|---|---|---|---|---|---|---|---|---|
| 20:00 | 59 | 38.3 | 28.3 | 41.0 | 0.881 | 72.7 | 0.932 | 83.6 | 1.00 |
| 21:00 | 59 | 38.2 | 32.3 | 41.0 | 0.864 | 70.5 | 0.881 | 77.9 | 1.00 |
| 22:00 | 59 | 37.1 | 35.0 | 41.0 | 0.864 | 68.2 | 0.898 | 76.1 | 1.00 |
| 23:00 | 59 | 37.1 | 30.3 | 41.0 | 0.814 | 65.8 | 0.881 | 72.7 | 1.00 |
| 00:00 | 59 | 37.0 | 35.0 | 41.0 | 0.797 | 63.3 | 0.864 | 73.3 | 1.00 |
| 01:00 | 60 | 36.1 | 29.8 | 40.8 | 0.817 | 60.7 | 0.867 | 71.9 | 1.00 |
| 02:00 | 60 | 36.0 | 31.4 | 40.8 | 0.767 | 58.0 | 0.900 | 70.8 | 1.00 |
| 03:00 | 60 | 35.6 | 33.5 | 40.8 | 0.733 | 55.2 | 0.917 | 69.8 | 1.00 |
| 04:00 | 60 | 33.8 | 30.8 | 40.8 | 0.800 | 52.2 | 0.900 | 66.4 | 1.00 |

Overnight prints (Blue Ocean, 5-minute bars): 4873 of 5760 slots traded on 58 nights. Same-instant traded bars against the close-anchored reference: 3951 bars, mean premium -2.4 bps, median absolute 4.9 bps, 90th percentile 15.8 bps; against the NAV-anchored reference, median absolute 5.8 bps. Traded bars left out because their futures price was up to 55 minutes older than the print (hourly bars only): 881, median absolute 5.0 bps.

| Hour (ET) | same-instant traded bars | mean premium (bps) | median abs (bps) |
|---|---|---|---|
| 20 | 525 | -1.6 | 4.9 |
| 21 | 514 | -2.5 | 4.8 |
| 22 | 494 | -2.8 | 5.1 |
| 23 | 476 | -2.7 | 5.1 |
| 00 | 462 | -2.6 | 5.3 |
| 01 | 488 | -2.9 | 4.8 |
| 02 | 490 | -2.4 | 4.6 |
| 03 | 502 | -2.0 | 4.6 |

Trading band, calibrated on same-instant traded prints 2026-08-13 to 2026-09-24 (1335 prints; 90th percentile 14.5 bps, median 4.2 bps) and applied to 2026-09-25 to 2026-11-05: covered 0.870 of 2616 prints; mean half-width 13.9 bps against 73.6 bps for the open band at the same hours.

## LQD — iShares iBoxx $ IG Corporate Bond ETF

Kind A, hedge ZN=F, beta 1.093. NAV source: file. Overnight tape: tiingo_boats.

| Hour (ET) | n | MAE ref (bps) | Median ref (bps) | MAE naive (bps) | Coverage Gaussian | Half-band Gaussian (bps) | Coverage empirical | Half-band empirical (bps) | Usable share |
|---|---|---|---|---|---|---|---|---|---|
| 20:00 | 59 | 22.6 | 21.0 | 24.3 | 0.814 | 41.1 | 0.898 | 48.2 | 1.00 |
| 21:00 | 59 | 22.5 | 19.1 | 24.3 | 0.797 | 40.3 | 0.881 | 46.0 | 1.00 |
| 22:00 | 59 | 21.8 | 18.6 | 24.3 | 0.831 | 39.5 | 0.864 | 45.8 | 1.00 |
| 23:00 | 59 | 21.3 | 19.5 | 24.3 | 0.814 | 38.6 | 0.847 | 45.0 | 1.00 |
| 00:00 | 59 | 21.9 | 19.9 | 24.3 | 0.814 | 37.8 | 0.847 | 44.8 | 1.00 |
| 01:00 | 60 | 22.0 | 18.8 | 24.3 | 0.817 | 36.9 | 0.883 | 44.8 | 1.00 |
| 02:00 | 60 | 21.9 | 20.2 | 24.3 | 0.833 | 36.0 | 0.900 | 45.0 | 1.00 |
| 03:00 | 60 | 21.2 | 20.0 | 24.3 | 0.833 | 35.0 | 0.900 | 43.4 | 1.00 |
| 04:00 | 60 | 20.1 | 16.8 | 24.3 | 0.850 | 34.1 | 0.917 | 41.2 | 1.00 |

Overnight prints (Blue Ocean, 5-minute bars): 131 of 5760 slots traded on 45 nights. Same-instant traded bars against the close-anchored reference: 113 bars, mean premium -3.6 bps, median absolute 6.2 bps, 90th percentile 24.4 bps; against the NAV-anchored reference, median absolute 8.4 bps. Traded bars left out because their futures price was up to 55 minutes older than the print (hourly bars only): 17, median absolute 5.4 bps.

| Hour (ET) | same-instant traded bars | mean premium (bps) | median abs (bps) |
|---|---|---|---|
| 20 | 16 | 0.5 | 5.6 |
| 21 | 25 | -7.9 | 6.6 |
| 22 | 9 | -4.4 | 4.2 |
| 23 | 9 | 0.5 | 5.7 |
| 00 | 5 | 2.7 | 4.9 |
| 01 | 13 | -4.0 | 5.3 |
| 02 | 26 | 1.3 | 5.9 |
| 03 | 10 | -17.6 | 17.2 |

Trading band: not calibrated, only 44 same-instant traded prints in the calibration half (50 needed).

## GLD — SPDR Gold Shares

Kind A, hedge GC=F, beta 0.961. NAV source: close_anchor. Overnight tape: tiingo_boats.

| Hour (ET) | n | MAE ref (bps) | Median ref (bps) | MAE naive (bps) | Coverage Gaussian | Half-band Gaussian (bps) | Coverage empirical | Half-band empirical (bps) | Usable share |
|---|---|---|---|---|---|---|---|---|---|
| 20:00 | 59 | 95.2 | 80.0 | 96.7 | 0.847 | 172.8 | 0.847 | 164.7 | 1.00 |
| 21:00 | 59 | 87.4 | 73.7 | 96.7 | 0.898 | 166.7 | 0.797 | 155.1 | 1.00 |
| 22:00 | 59 | 85.9 | 74.2 | 96.7 | 0.915 | 160.4 | 0.729 | 137.4 | 1.00 |
| 23:00 | 59 | 77.8 | 51.8 | 96.7 | 0.881 | 153.7 | 0.881 | 139.1 | 1.00 |
| 00:00 | 59 | 73.5 | 53.9 | 96.7 | 0.898 | 146.8 | 0.831 | 129.7 | 1.00 |
| 01:00 | 60 | 69.3 | 52.4 | 96.4 | 0.917 | 139.6 | 0.900 | 131.0 | 1.00 |
| 02:00 | 60 | 62.1 | 45.9 | 96.4 | 0.900 | 131.9 | 0.883 | 118.9 | 1.00 |
| 03:00 | 60 | 57.3 | 46.7 | 96.4 | 0.900 | 123.8 | 0.833 | 106.1 | 1.00 |
| 04:00 | 60 | 53.1 | 43.2 | 96.4 | 0.883 | 115.1 | 0.817 | 103.9 | 1.00 |

Overnight prints (Blue Ocean, 5-minute bars): 5675 of 5760 slots traded on 60 nights. Same-instant traded bars against the close-anchored reference: 4570 bars, mean premium 2.0 bps, median absolute 2.6 bps, 90th percentile 7.3 bps; against the NAV-anchored reference, median absolute 2.6 bps. Traded bars left out because their futures price was up to 55 minutes older than the print (hourly bars only): 1057, median absolute 10.6 bps.

| Hour (ET) | same-instant traded bars | mean premium (bps) | median abs (bps) |
|---|---|---|---|
| 20 | 571 | 1.6 | 2.2 |
| 21 | 573 | 1.8 | 2.5 |
| 22 | 570 | 1.9 | 2.6 |
| 23 | 563 | 2.1 | 2.7 |
| 00 | 560 | 2.3 | 2.6 |
| 01 | 572 | 2.3 | 2.8 |
| 02 | 578 | 2.2 | 2.7 |
| 03 | 583 | 2.1 | 3.0 |

Trading band, calibrated on same-instant traded prints 2026-08-13 to 2026-09-24 (1761 prints; 90th percentile 6.5 bps, median 2.5 bps) and applied to 2026-09-25 to 2026-11-05: covered 0.827 of 2809 prints; mean half-width 6.4 bps against 131.8 bps for the open band at the same hours.

## IBIT — iShares Bitcoin Trust ETF

Kind C, hedge BTC-USD, beta 1.012. NAV source: file. Overnight tape: tiingo_boats.

| Hour (ET) | n | MAE ref (bps) | Median ref (bps) | MAE naive (bps) | Coverage Gaussian | Half-band Gaussian (bps) | Coverage empirical | Half-band empirical (bps) | Usable share |
|---|---|---|---|---|---|---|---|---|---|
| 20:00 | 60 | 122.4 | 92.8 | 140.3 | 0.950 | 287.8 | 0.950 | 276.6 | 1.00 |
| 21:00 | 60 | 119.5 | 93.8 | 140.3 | 0.950 | 277.4 | 0.917 | 260.6 | 1.00 |
| 22:00 | 60 | 109.9 | 91.0 | 140.3 | 0.933 | 266.5 | 0.917 | 241.2 | 1.00 |
| 23:00 | 60 | 103.8 | 84.7 | 140.3 | 0.933 | 255.2 | 0.917 | 234.7 | 1.00 |
| 00:00 | 60 | 99.9 | 86.2 | 140.3 | 0.933 | 243.4 | 0.900 | 228.3 | 1.00 |
| 01:00 | 60 | 96.5 | 82.3 | 140.3 | 0.917 | 230.9 | 0.900 | 223.5 | 1.00 |
| 02:00 | 60 | 93.4 | 66.2 | 140.3 | 0.883 | 217.7 | 0.883 | 196.0 | 1.00 |
| 03:00 | 60 | 85.8 | 62.7 | 140.3 | 0.900 | 203.7 | 0.883 | 191.1 | 1.00 |
| 04:00 | 60 | 75.6 | 50.5 | 140.3 | 0.917 | 188.7 | 0.900 | 164.2 | 1.00 |

Overnight prints (Blue Ocean, 5-minute bars): 5529 of 5760 slots traded on 60 nights. Same-instant traded bars against the close-anchored reference: 3838 bars, mean premium -1.3 bps, median absolute 3.6 bps, 90th percentile 7.4 bps; against the NAV-anchored reference, median absolute 10.9 bps. Traded bars left out because their futures price was up to 55 minutes older than the print (hourly bars only): 1691, median absolute 14.8 bps.

| Hour (ET) | same-instant traded bars | mean premium (bps) | median abs (bps) |
|---|---|---|---|
| 20 | 485 | -1.3 | 3.3 |
| 21 | 489 | -1.3 | 3.5 |
| 22 | 488 | -1.3 | 3.8 |
| 23 | 476 | -1.0 | 3.5 |
| 00 | 472 | -1.3 | 3.6 |
| 01 | 470 | -1.3 | 3.6 |
| 02 | 474 | -1.5 | 3.9 |
| 03 | 484 | -1.3 | 3.4 |

Trading band, calibrated on same-instant traded prints 2026-08-13 to 2026-09-24 (1094 prints; 90th percentile 9.9 bps, median 3.3 bps) and applied to 2026-09-25 to 2026-11-05: covered 0.937 of 2744 prints; mean half-width 8.7 bps against 224.0 bps for the open band at the same hours.

## Footnotes

- Where no NAV file was supplied the 4pm close stands in for the NAV (`nav_proxy_close`). For US equity funds the difference is usually a few basis points; for international funds it can be larger because the official NAV fair-values foreign closes.
- The hedge move is measured to 9:00am and the fund opens at 9:30am. The half hour adds noise to the beta estimate; it does not add look-ahead.
- The exchanges' band uses the 7:45pm consolidated round-lot sale. Yahoo's 15-minute post-market bars thin out after 7pm, so the print used here is the last post-market bar before 7:45pm, often the bar ending 7:00pm; the time actually used is stored in each record (`sale_1945_time`). With a 20% band the difference is immaterial; the 1-minute extended-hours feed replaces it once a key is available.
- Hourly bars from Yahoo's chart feed are stamped at the bar's start; the value at an hour is the close of the bar that covers the hour before it. A print between hours is never paired with a bar that was still open when the print closed.
- 'Usable' is the trip-wire: every input fresh and the band not wider than 400 bps half-width.
- Two reference values are carried. The open-based grading uses the official NAV as the 4pm anchor where the issuer file provides it (the close for QQQ and SMH, and for GLD, whose NAV is struck off the London afternoon gold price). The print comparison and the trading band use the 4pm close as the anchor, because overnight trades price off the fund's own last trade; the NAV-anchored print figures are kept as `traded_nav_anchor`.
- On an ex-dividend morning the open is compared with the payout added back (`truth_open_cum`), because the shares open lower by the distribution through no fault of the hedge; overnight prints are cum-dividend and are left alone. Records carry the flag `exdiv:<amount>`.