"""Backwards-compatible re-exports of the pre-1.0 helper functions."""

from .legs import check_optype, check_trtype
from .payoff import payoff_calculator
from .yf import spot_price as check_ticker

__all__ = ["check_optype", "check_trtype", "payoff_calculator", "check_ticker"]
