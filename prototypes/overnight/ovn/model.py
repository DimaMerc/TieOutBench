"""The quantitative part: the exchanges' static band, overnight beta, the carry-forward reference
value, its band, and the trip-wire. Pure functions; no I/O."""
from __future__ import annotations
import math
import statistics

from .config import STATIC_BAND_PCT, STATIC_BAND_MIN_DOLLARS, BAND_Z


# ---------------- the exchanges' overnight band ----------------
def static_band(close: float, sale_1945: float | None) -> tuple[float, float]:
    """LULD overnight bands: lower = 20% under the LOWER reference, upper = 20% over the HIGHER
    reference, each at least $3 from its reference. References: 4pm close and the 7:45pm sale."""
    refs = [close] if sale_1945 is None else [close, sale_1945]
    lo_ref, hi_ref = min(refs), max(refs)
    lo = min(lo_ref * (1 - STATIC_BAND_PCT), lo_ref - STATIC_BAND_MIN_DOLLARS)
    hi = max(hi_ref * (1 + STATIC_BAND_PCT), hi_ref + STATIC_BAND_MIN_DOLLARS)
    return lo, hi


# ---------------- least squares (tiny, dense) ----------------
def ols(y: list, X: list) -> dict:
    """y = X b + e by normal equations with Gaussian elimination. X rows are lists (include a 1 for
    the intercept yourself). Returns {"b": [...], "sigma": residual std (ddof = p), "n": n, "r2": r2}."""
    n = len(y)
    if n == 0:
        raise ValueError("ols: empty sample")
    p = len(X[0])
    if n <= p:
        raise ValueError(f"ols: {n} rows for {p} parameters")
    XtX = [[sum(X[k][i] * X[k][j] for k in range(n)) for j in range(p)] for i in range(p)]
    Xty = [sum(X[k][i] * y[k] for k in range(n)) for i in range(p)]
    # solve XtX b = Xty
    A = [row[:] + [Xty[i]] for i, row in enumerate(XtX)]
    for c in range(p):
        piv = max(range(c, p), key=lambda r: abs(A[r][c]))
        if abs(A[piv][c]) < 1e-14:
            raise ValueError("ols: singular design")
        A[c], A[piv] = A[piv], A[c]
        for r in range(p):
            if r != c:
                f = A[r][c] / A[c][c]
                for k in range(c, p + 1):
                    A[r][k] -= f * A[c][k]
    b = [A[i][p] / A[i][i] for i in range(p)]
    resid = [y[k] - sum(b[i] * X[k][i] for i in range(p)) for k in range(n)]
    ss_res = sum(e * e for e in resid)
    ybar = sum(y) / n
    ss_tot = sum((v - ybar) ** 2 for v in y) or 1e-18
    sigma = math.sqrt(ss_res / (n - p))
    return {"b": b, "sigma": sigma, "n": n, "r2": 1 - ss_res / ss_tot}


def fit_overnight(train: list, use_fx: bool) -> dict:
    """train rows: {"y": fund overnight return, "rh": hedge return, "rfx": signed fx return or 0}.
    Fits y = a + beta*rh (+ gamma*rfx). Returns the fit plus the hourly hedge volatility input."""
    y = [r["y"] for r in train]
    if use_fx:
        X = [[1.0, r["rh"], r["rfx"]] for r in train]
    else:
        X = [[1.0, r["rh"]] for r in train]
    f = ols(y, X)
    out = {"alpha": f["b"][0], "beta": f["b"][1], "gamma": f["b"][2] if use_fx else 0.0,
           "sigma_resid": f["sigma"], "n_train": f["n"], "r2": f["r2"], "use_fx": use_fx}
    return out


def hourly_sigma(log_returns: list) -> float:
    """Std of hourly log returns of the hedge during overnight hours (train period)."""
    xs = [x for x in log_returns if x is not None and math.isfinite(x)]
    if len(xs) < 30:
        return float("nan")
    return statistics.pstdev(xs)


# ---------------- reference value and band ----------------
def carry_forward(nav: float, fit: dict, rh: float, rfx: float = 0.0) -> float:
    """Reference value at an hour: NAV moved by the hedge (and currency) since 4pm. Alpha is NOT
    applied (no drift term in the published value)."""
    return nav * (1.0 + fit["beta"] * rh + fit["gamma"] * rfx)


def band(center: float, fit: dict, sigma_hr: float, hours_remaining: float, z: float = BAND_Z) -> tuple[float, float, float]:
    """Half-width = z * sqrt(residual variance + beta^2 * hourly hedge variance * hours left).
    Returns (lo, hi, half_width_bps)."""
    var = fit["sigma_resid"] ** 2
    if sigma_hr == sigma_hr and hours_remaining > 0:  # not NaN
        var += (fit["beta"] ** 2) * (sigma_hr ** 2) * hours_remaining
    half = z * math.sqrt(var)
    return center * (1 - half), center * (1 + half), half * 1e4


def empirical_quantiles(abs_errors: list, qs=(0.5, 0.9)) -> dict:
    """Plain order-statistic quantiles of absolute errors (fractions of NAV). No distribution assumed."""
    xs = sorted(e for e in abs_errors if e is not None and math.isfinite(e))
    out = {"n": len(xs)}
    for q in qs:
        out[f"q{int(q*100)}"] = xs[int(q * (len(xs) - 1))] if xs else None
    return out


def empirical_band(center: float, q: float) -> tuple[float, float, float]:
    """Band whose half-width is the training-set quantile of the carry-forward's own error at this
    hour. Returns (lo, hi, half_width_bps)."""
    return center * (1 - q), center * (1 + q), q * 1e4


def trip_wire(inputs_ok: bool, stale: list, half_bps: float, max_half_bps: float = 400.0) -> str:
    """'usable' when every input is fresh and the band is not absurdly wide; otherwise 'unreliable'
    with the reason. Mirrors the money-fund order's logic: a published value with a stated tolerance
    and a rule for when it stops being published."""
    if not inputs_ok:
        return "unreliable:missing_input"
    if stale:
        return "unreliable:stale:" + ",".join(stale)
    if half_bps > max_half_bps:
        return "unreliable:band_too_wide"
    return "usable"
