"""Vectorised Black-Scholes-Merton pricing and greeks."""

from __future__ import annotations

import numpy as np
from scipy.stats import norm


def _out(a):
    """Return a Python float for 0-d results, else the array."""
    a = np.asarray(a, dtype=float)
    return float(a) if a.ndim == 0 else a


def black_scholes(t=40, r=4.00, v=32.00, K=60, St=62, type="c", q=0.0):
    """Black-Scholes-Merton option value and greeks.

    Every numeric argument may be a scalar or a NumPy array (broadcast
    together), so whole surfaces can be computed in one call.

    Parameters
    ----------
    t : float or array
        Time to expiration in days.
    r : float or array
        Risk-free rate in percent (4 = 4%).
    v : float or array
        Volatility in percent.
    K : float or array
        Exercise (strike) price.
    St : float or array
        Current underlying price.
    type : {'c', 'p'}
        Call or put.
    q : float or array, default 0
        Continuous dividend yield in percent.

    Returns
    -------
    dict
        ``{'value': {'option value', 'intrinsic value', 'time value'},
        'greeks': {'delta', 'gamma', 'theta', 'vega', 'rho'}}``.
        Theta is per calendar day; vega and rho are per 1 percentage point.
    """
    is_call = str(type).lower() == "c"

    t, r, v, K, St, q = np.broadcast_arrays(
        *(np.asarray(a, dtype=float) for a in (t, r, v, K, St, q))
    )
    T = t / 365.0
    r, v, q = r / 100.0, v / 100.0, q / 100.0

    live = T > 0
    Ts = np.where(live, T, 1.0)  # safe denominator; expired values masked below
    sqrtT = np.sqrt(Ts)
    with np.errstate(divide="ignore", invalid="ignore"):
        d1 = (np.log(St / K) + (r - q + v**2 / 2) * Ts) / (v * sqrtT)
    d2 = d1 - v * sqrtT

    disc_r = np.exp(-r * Ts)
    disc_q = np.exp(-q * Ts)
    pdf_d1 = norm.pdf(d1)

    if is_call:
        val = St * disc_q * norm.cdf(d1) - K * disc_r * norm.cdf(d2)
        intrinsic = np.maximum(St - K, 0.0)
        delta = disc_q * norm.cdf(d1)
        theta = (
            -St * pdf_d1 * v * disc_q / (2 * sqrtT)
            - r * K * disc_r * norm.cdf(d2)
            + q * St * disc_q * norm.cdf(d1)
        )
        rho = K * Ts * disc_r * norm.cdf(d2) / 100
        expired_delta = (St > K).astype(float)
    else:
        val = K * disc_r * norm.cdf(-d2) - St * disc_q * norm.cdf(-d1)
        intrinsic = np.maximum(K - St, 0.0)
        delta = -disc_q * norm.cdf(-d1)
        theta = (
            -St * pdf_d1 * v * disc_q / (2 * sqrtT)
            + r * K * disc_r * norm.cdf(-d2)
            - q * St * disc_q * norm.cdf(-d1)
        )
        rho = -K * Ts * disc_r * norm.cdf(-d2) / 100
        expired_delta = -(St < K).astype(float)

    gamma = disc_q * pdf_d1 / (St * v * sqrtT)
    vega = St * disc_q * pdf_d1 * sqrtT / 100
    theta = theta / 365

    # At/after expiry the option is worth its intrinsic value only.
    val = np.where(live, val, intrinsic)
    delta = np.where(live, delta, expired_delta)
    gamma, theta, vega, rho = (np.where(live, g, 0.0) for g in (gamma, theta, vega, rho))

    return {
        "value": {
            "option value": _out(val),
            "intrinsic value": _out(intrinsic),
            "time value": _out(val - intrinsic),
        },
        "greeks": {
            "delta": _out(delta),
            "gamma": _out(gamma),
            "theta": _out(theta),
            "vega": _out(vega),
            "rho": _out(rho),
        },
    }
