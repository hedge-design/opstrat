"""Vectorised payoff-at-expiry calculations and strategy statistics."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

import numpy as np

from .legs import Leg, to_legs


def leg_payoff(x: np.ndarray, leg: Leg) -> np.ndarray:
    """Profit/loss of one leg at expiry for each underlying price in ``x``."""
    x = np.asarray(x, dtype=float)
    if leg.op_type == "c":
        intrinsic = np.maximum(x - leg.strike, 0.0)
    else:
        intrinsic = np.maximum(leg.strike - x, 0.0)
    return leg.sign * (intrinsic - leg.op_pr) * leg.contracts


def payoff_calculator(x, op_type, strike, op_pr, tr_type, n=1):
    """Legacy helper kept for backwards compatibility."""
    return leg_payoff(x, Leg(op_type, strike, tr_type, op_pr, n))


def strategy_payoff(x: np.ndarray, op_list: Iterable[Leg | Mapping]) -> np.ndarray:
    """Combined profit/loss of all legs at expiry."""
    legs = to_legs(op_list)
    return np.sum([leg_payoff(x, leg) for leg in legs], axis=0)


@dataclass(frozen=True)
class StrategySummary:
    """Exact expiry statistics for a strategy over prices in [0, inf).

    ``max_profit`` / ``max_loss`` are ``inf`` when unbounded. ``max_loss`` is
    reported as a non-positive number.
    """

    breakevens: tuple[float, ...]
    max_profit: float
    max_loss: float
    net_premium: float  # positive = credit received, negative = debit paid


def summarize(op_list: Iterable[Leg | Mapping]) -> StrategySummary:
    """Compute breakevens and max profit/loss exactly.

    The expiry payoff is piecewise linear with kinks only at strikes, so the
    extremes occur at S=0, at a strike, or at S -> inf (governed by the net
    call position). Breakevens are found by solving each linear segment.
    """
    legs = to_legs(op_list)
    kinks = np.unique([0.0] + [leg.strike for leg in legs])
    y = strategy_payoff(kinks, legs)
    # Slope beyond the highest strike: only calls contribute.
    tail_slope = sum(leg.sign * leg.contracts for leg in legs if leg.op_type == "c")

    max_profit = np.inf if tail_slope > 0 else float(y.max())
    max_loss = -np.inf if tail_slope < 0 else float(y.min())

    breakevens: list[float] = []
    for (x0, y0), (x1, y1) in zip(zip(kinks, y), zip(kinks[1:], y[1:])):
        if y0 == 0 and (not breakevens or not np.isclose(breakevens[-1], x0)):
            breakevens.append(float(x0))
        if y0 * y1 < 0:
            breakevens.append(float(x0 - y0 * (x1 - x0) / (y1 - y0)))
    if y[-1] == 0 and (not breakevens or not np.isclose(breakevens[-1], kinks[-1])):
        breakevens.append(float(kinks[-1]))
    if tail_slope != 0 and y[-1] * tail_slope < 0:
        breakevens.append(float(kinks[-1] - y[-1] / tail_slope))

    net_premium = float(sum(-leg.sign * leg.op_pr * leg.contracts for leg in legs))
    return StrategySummary(
        breakevens=tuple(b for b in breakevens if b > 0),
        max_profit=max_profit,
        max_loss=min(max_loss, 0.0),
        net_premium=net_premium,
    )
