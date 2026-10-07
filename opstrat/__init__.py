"""opstrat - interactive option strategy visualisation with Plotly."""

__version__ = "2.0.0"
__author__ = "Abhijith Chandradas"

from .blackscholes import black_scholes
from .legs import Leg
from .payoff import StrategySummary, leg_payoff, strategy_payoff, summarize
from .plotting import greeks_plotter, multi_plotter, payoff_figure, single_plotter
from .yf import yf_plotter

__all__ = [
    "Leg",
    "StrategySummary",
    "black_scholes",
    "greeks_plotter",
    "leg_payoff",
    "multi_plotter",
    "payoff_figure",
    "single_plotter",
    "strategy_payoff",
    "summarize",
    "yf_plotter",
]
