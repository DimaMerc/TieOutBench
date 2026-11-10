"""Fund list, hedge instruments and the handful of parameters the model uses.

Night kinds (see the draft paper, section 4):
  A  the fund holds US assets; the hedge trades through the night (futures), the ETF's own stocks
     trade thinly once the exchanges open overnight sessions on 2026-12-06.
  B  the fund holds foreign assets; the local market is open during part of the US night.
  C  the fund's underlying trades every hour of every day (bitcoin), or nothing trades (weekends).

`hedges` is an ordered list: the first symbol with data is used, the rest are fallbacks and the
record is flagged when a fallback was needed. `fx` is the currency pair whose move adds to the
fund's return; `fx_dir` is +1 when a rise in the quoted pair helps a US-dollar holder and -1 when it
hurts (JPY=X is yen per dollar, so a rise means a weaker yen and a lower EWJ).
"""
from __future__ import annotations

ET = "America/New_York"

FUNDS = {
    "SPY":  {"name": "SPDR S&P 500 ETF Trust",             "kind": "A", "hedges": ["ES=F"],  "fx": None,       "fx_dir": 0,  "local": []},
    "QQQ":  {"name": "Invesco QQQ Trust",                  "kind": "A", "hedges": ["NQ=F"],  "fx": None,       "fx_dir": 0,  "local": []},
    "SMH":  {"name": "VanEck Semiconductor ETF",           "kind": "A", "hedges": ["NQ=F"],  "fx": None,       "fx_dir": 0,  "local": []},
    "EWJ":  {"name": "iShares MSCI Japan ETF",             "kind": "B", "hedges": ["NIY=F", "ES=F"], "fx": "JPY=X",    "fx_dir": -1, "local": ["^N225"]},
    "EWG":  {"name": "iShares MSCI Germany ETF",           "kind": "B", "hedges": ["ES=F"],  "fx": "EURUSD=X", "fx_dir": +1, "local": ["^GDAXI"]},
    "EEM":  {"name": "iShares MSCI Emerging Markets ETF",  "kind": "B", "hedges": ["MME=F", "ES=F"], "fx": None, "fx_dir": 0, "local": ["^HSI", "^KS11"]},
    "TLT":  {"name": "iShares 20+ Year Treasury Bond ETF", "kind": "A", "hedges": ["ZB=F"],  "fx": None,       "fx_dir": 0,  "local": []},
    "LQD":  {"name": "iShares iBoxx $ IG Corporate Bond ETF", "kind": "A", "hedges": ["ZN=F"], "fx": None,     "fx_dir": 0,  "local": []},
    # GLD's official NAV is struck off the LBMA afternoon gold price (about 10am New York), not at 4pm;
    # the 4pm close is the better anchor for an overnight value, so the NAV file is read but not used
    "GLD":  {"name": "SPDR Gold Shares",                   "kind": "A", "hedges": ["GC=F"],  "fx": None,       "fx_dir": 0,  "local": [], "nav_anchor": "close"},
    "IBIT": {"name": "iShares Bitcoin Trust ETF",          "kind": "C", "hedges": ["BTC-USD"], "fx": None,     "fx_dir": 0,  "local": []},
}

# Reference-value grid: wall-clock hours (ET) on the night before the next trading day.
# 20 to 23 fall on the calendar day before; 0 to 4 on the trading day itself.
GRID_HOURS = [20, 21, 22, 23, 0, 1, 2, 3, 4]

# The exchanges' overnight band (LULD plan amendment, SEC Rel. 34-105596): 20% off the lower and the
# higher of the 4pm close and the 7:45pm consolidated round-lot sale, never closer than $3.
STATIC_BAND_PCT = 0.20
STATIC_BAND_MIN_DOLLARS = 3.00

# Nominal confidence of the model band and its normal quantile (two-sided 90%).
BAND_CONFIDENCE = 0.90
BAND_Z = 1.6449

# Hours that may pass since an instrument's last bar before its signal is declared stale at a grid hour.
STALE_HOURS = {"default": 2.5, "^N225": 20.0, "^GDAXI": 20.0, "^HSI": 20.0, "^KS11": 20.0,
               "^TWII": 20.0, "^BSESN": 20.0, "^FTSE": 20.0, "^STOXX50E": 20.0, "^BVSP": 20.0}

# How many trading nights before the test window are used to estimate beta and residual spread.
MIN_TRAIN_NIGHTS = 120

# Evidence layer: how many of the fund's largest holdings are read for news.
EVIDENCE_TOP_HOLDINGS = 10

# Models for the evidence layer, through the harness's OpenAI-compatible client.
# Haiku sweeps every fund-night cheaply; Sonnet is the primary; Opus adjudicates a sample.
EVIDENCE_MODELS = {
    "haiku":  {"endpoint": "https://api.anthropic.com/v1", "model_id": "claude-haiku-5-5"},
    "sonnet": {"endpoint": "https://api.anthropic.com/v1", "model_id": "claude-sonnet-5-5"},
    "opus":   {"endpoint": "https://api.anthropic.com/v1", "model_id": "claude-opus-5-5"},
    # the cost column: whatever model LM Studio has loaded on the local machine (model_id None lets the
    # harness pick the served model). Prompts run 25-30k tokens, so load the model with a context of at
    # least 40k; a 7-9B model at Q4 fits that on a 12 GB card.
    "local":  {"endpoint": "http://localhost:1234/v1", "model_id": None},
    # the 9B column, pinned by name so it never falls back to whatever else is loaded. With its default
    # thinking the model spent 7,865 reasoning tokens on one 12k-token prompt and never answered inside
    # an 8,000-token cap; LM Studio honours reasoning_effort "none" (0 reasoning tokens, 2.5 s on a
    # tiny prompt), so the column runs without thinking and the paper says so.
    "local9b": {"endpoint": "http://localhost:1234/v1", "model_id": "qwen3.5-9b",
                "extra": {"reasoning_effort": "none"}},
}
