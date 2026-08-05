#!/usr/bin/env python3
"""
cases/_dcf_gold_nvda.py — compute the eval-#3 GOLD DCF for the NVIDIA FY2026 case,
closed-form, so the case YAML carries verifiable numbers (no hand arithmetic).

Base lines are REAL FY2026 10-K figures (accession 0001045810-26-000021, $M, fiscal
year ended 2026-01-25):
  revenue 215,938 | operating income (EBIT) 130,387 | tax expense 21,383 | pre-tax 141,450
  net income 120,067 | D&A 2,843 | capex 6,042 ('Purchases related to property and equipment
  and intangible assets') | SBC 6,386 (expensed in EBIT; NOT added back — see case note)
  cash 10,605 | marketable securities 51,951 | short-term debt 999 + long-term debt 7,469
  = total debt 8,468 | non-marketable equity securities 22,251 (non-op; ADD in bridge)
  diluted wtd-avg shares 24,514M | diluted EPS 4.90
The FORECAST + WACC + terminal are the ORACLE layer (illustrative, labeled). Convention:
year-end. The company is NET CASH: net debt = 8,468 - 62,556 = -54,088 — the EV->equity
bridge ADDS value, the mirror of the MCD case. Run: python cases/_dcf_gold_nvda.py
"""

# ---------------- REAL FY2026 base (filed, $M) ----------------
REV0       = 215_938.0
EBIT0      = 130_387.0
DA0        = 2_843.0
CAPEX0     = 6_042.0
CASH       = 10_605.0
MKT_SEC    = 51_951.0
TOTAL_DEBT = 999.0 + 7_469.0            # Short-term debt + Long-term debt (two additive face lines)
NET_DEBT   = TOTAL_DEBT - CASH - MKT_SEC   # -54,088 (NET CASH — the bridge adds)
NONOP      = 22_251.0                   # non-marketable equity securities (gains sit in Other
                                        # income, NOT in EBIT -> ADD in bridge)
MINORITY   = 0.0
PREFERRED  = 0.0
SHARES     = 24_514.0                   # diluted weighted-average, millions

# ---------------- ORACLE forecast (illustrative, labeled) ----------------
H          = 5                          # explicit horizon (FY2027-2031)
REV_GROWTH = [0.35, 0.25, 0.18, 0.12, 0.08]         # decelerating hypergrowth
MARGINS    = [0.5931, 0.5823, 0.5715, 0.5608, 0.5500]  # EBIT margin fades 60.38% -> 55.0%
CASH_TAX   = 0.155                      # ~ the 15.1% FY2026 effective rate
DA_PCT     = 0.013166                   # DA0/REV0 rounded to the STATED oracle constant (gold = f(stated))
CAPEX_PCT  = 0.027980                   # CAPEX0/REV0 rounded to the STATED oracle constant
NWC_PCT_OF_DELTA_REV = 0.12             # dNWC = 12% of each year's incremental revenue
DNWC_STATED = [9069.4, 8745.5, 7870.9, 6191.8, 4623.2]  # the 1dp vector the case STATES (gold = f(stated))

# ---------------- ORACLE WACC components ----------------
RF     = 0.043
BETA   = 1.70
ERP    = 0.050
KD_PRE = 0.046
W_D    = 0.02                           # target market debt weight (~$8.5B debt on a ~$4-5T cap)
W_E    = 1.0 - W_D
KE     = RF + BETA * ERP                # 12.80%
KD_AFT = KD_PRE * (1 - CASH_TAX)        # 3.887%
WACC   = W_E * KE + W_D * KD_AFT        # ~12.62%

# ---------------- ORACLE terminal ----------------
G = 0.04                                # Gordon g (~long-run nominal GDP; << WACC 12.62%)

PRICE = 206.64                          # real Nasdaq close, 2026-08-03 (oracle snapshot)


def fcff_path():
    rows = []
    rev_prev = REV0
    for t in range(1, H + 1):
        rev   = rev_prev * (1 + REV_GROWTH[t - 1])
        ebit  = rev * MARGINS[t - 1]
        nopat = ebit * (1 - CASH_TAX)
        da    = rev * DA_PCT
        capex = rev * CAPEX_PCT
        dnwc  = DNWC_STATED[t - 1]      # = round(NWC_PCT_OF_DELTA_REV * (rev - rev_prev), 1); use the STATED vector
        fcff  = nopat + da - capex - dnwc
        rows.append(dict(t=t, rev=rev, ebit=ebit, nopat=nopat, da=da, capex=capex, dnwc=dnwc, fcff=fcff))
        rev_prev = rev
    return rows


def value(rows, wacc, g):
    pvs = sum(r["fcff"] / (1 + wacc) ** r["t"] for r in rows)
    fcff_N = rows[-1]["fcff"]
    tv = fcff_N * (1 + g) / (wacc - g)
    pv_tv = tv / (1 + wacc) ** H
    ev = pvs + pv_tv
    eq = ev - NET_DEBT - MINORITY - PREFERRED + NONOP
    return pvs, tv, pv_tv, ev, eq, eq / SHARES


def main():
    print(f"DA%={DA_PCT:.4%}  capex%={CAPEX_PCT:.4%}  net_debt={NET_DEBT:,.0f} (NET CASH)")
    print(f"Ke={KE:.4%}  Kd_after={KD_AFT:.4%}  WACC={WACC:.6%}  g={G:.2%}")
    rows = fcff_path()
    print("\n yr      revenue       ebit      nopat      d&a     capex     dnwc      fcff       df        pv")
    pv_sum = 0.0
    for r in rows:
        df = 1 / (1 + WACC) ** r["t"]
        pv = r["fcff"] * df
        pv_sum += pv
        print(f"  {r['t']}  {r['rev']:11,.1f} {r['ebit']:10,.1f} {r['nopat']:10,.1f} {r['da']:8,.1f} "
              f"{r['capex']:8,.1f} {r['dnwc']:8,.1f} {r['fcff']:9,.1f}  {df:.5f}  {pv:9,.1f}")
    pvs, tv, pv_tv, ev, eq, ps = value(rows, WACC, G)
    tv_share = pv_tv / ev
    implied_exit = tv / rows[-1]["ebit"]
    print(f"\n sum PV(FCFF) = {pvs:,.1f}")
    print(f" TV (undisc)  = {tv:,.1f}    PV(TV) = {pv_tv:,.1f}    TV share of EV = {tv_share:.2%}")
    print(f" implied exit EV/EBIT (terminal) = {implied_exit:.2f}x")
    print(f" EV           = {ev:,.1f}")
    print(f" - net debt {NET_DEBT:,.0f} (i.e. + net cash)  + non-op {NONOP:,.0f}")
    print(f" equity       = {eq:,.1f}")
    print(f" per share    = {ps:,.2f}  (on {SHARES:,.0f}M diluted)   price {PRICE}  upside {(ps/PRICE-1):+.2%}")
    print(f" EV/shares blunder = {ev/SHARES:,.2f}  (UNDERSTATES the correct {ps:,.2f} by the net-cash bridge "
          f"{(NONOP - NET_DEBT)/SHARES:,.2f}/share = {(ev/SHARES)/ps-1:+.2%})")

    # ---- sensitivity grid: per-share over WACC x g ----
    print("\n sensitivity (per share):   g across, WACC down")
    gs = [G - 0.005, G, G + 0.005]
    ws = [WACC - 0.005, WACC, WACC + 0.005]
    print("  WACC\\g   " + "".join(f"{g:8.2%}" for g in gs))
    grid = {}
    for w in ws:
        line = f"  {w:7.3%} "
        for g in gs:
            _, _, _, _, _, p = value(rows, w, g)
            grid[(round(w, 5), round(g, 5))] = p
            line += f"{p:8,.2f}"
        print(line)
    ps_lowW  = grid[(round(WACC - 0.005, 5), round(G, 5))]
    ps_highW = grid[(round(WACC + 0.005, 5), round(G, 5))]
    print(f"\n per-share at base g: WACC-50bp={ps_lowW:,.2f}  base={ps:,.2f}  WACC+50bp={ps_highW:,.2f}")
    print(f" +-50bp WACC swing: {(ps_lowW-ps)/ps:+.2%} / {(ps_highW-ps)/ps:+.2%}")
    g_low  = grid[(round(WACC, 5), round(G - 0.005, 5))]
    g_high = grid[(round(WACC, 5), round(G + 0.005, 5))]
    print(f" +-50bp g swing:    {(g_high-ps)/ps:+.2%} / {(g_low-ps)/ps:+.2%}")


if __name__ == "__main__":
    main()
