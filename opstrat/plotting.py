"""Interactive Plotly payoff and greeks plots."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ._theme import (
    OpstratFigure,
    base_layout,
    finish,
    resolve_theme,
    series_color,
    tokens,
    toolbar_config,
)
from .blackscholes import black_scholes
from .legs import NAMES, Leg, to_legs
from .payoff import leg_payoff, strategy_payoff, summarize

DEFAULT_LEGS = (
    {"op_type": "c", "strike": 110, "tr_type": "s", "op_pr": 2, "contracts": 1},
    {"op_type": "p", "strike": 95, "tr_type": "s", "op_pr": 6, "contracts": 1},
)


def _fmt(v: float) -> str:
    if np.isinf(v):
        return "Unlimited"
    return f"{v:,.2f}"


def _subtitle(legs: list[Leg]) -> str:
    s = summarize(legs)
    be = ", ".join(f"{b:,.2f}" for b in s.breakevens) or "none"
    loss = "Unlimited" if np.isinf(s.max_loss) else f"{s.max_loss:,.2f}"
    return f"Max profit {_fmt(s.max_profit)}  ·  Max loss {loss}  ·  Breakeven {be}"


def payoff_figure(
    op_list: Iterable[Leg | Mapping],
    spot: float,
    spot_range: float = 20,
    title: str = "Option strategy payoff at expiry",
    theme: str | None = None,
    show_legs: bool = True,
    show_title: bool = True,
    show_subtitle: bool = True,
    show_toolbar: bool = True,
) -> go.Figure:
    """Build the payoff-at-expiry figure for any list of legs.

    Shaded regions mark profit (blue) and loss (red); individual legs are
    dashed, the combined position is the solid line.

    Parameters
    ----------
    show_title, show_subtitle, show_toolbar : bool, default True
        Set False to hide the chart title, the max profit / max loss /
        breakeven subtitle, or the Plotly toolbar (modebar).
    """
    legs = to_legs(op_list)
    theme = resolve_theme(theme)
    if spot <= 0:
        raise ValueError("spot must be positive")
    if not 0 < spot_range < 100:
        raise ValueError("spot_range must be between 0 and 100 (percent)")
    t = tokens(theme)
    summary = summarize(legs)

    lo, hi = spot * (1 - spot_range / 100), spot * (1 + spot_range / 100)
    extra = [k.strike for k in legs] + list(summary.breakevens)
    x = np.linspace(lo, hi, 1001)
    x = np.unique(np.concatenate([x, [e for e in extra if lo <= e <= hi]]))
    y = strategy_payoff(x, legs)

    fig = OpstratFigure(plotly_config=toolbar_config(show_toolbar))
    for clip, color, name in ((np.maximum, t["profit"], "Profit"),
                              (np.minimum, t["loss"], "Loss")):
        fig.add_trace(go.Scatter(
            x=x, y=clip(y, 0), fill="tozeroy", fillcolor=color, mode="none",
            name=name, hoverinfo="skip", showlegend=False,
        ))

    multi = len(legs) > 1
    if multi and show_legs:
        for i, leg in enumerate(legs):
            fig.add_trace(go.Scatter(
                x=x, y=leg_payoff(x, leg), mode="lines", name=leg.label,
                line=dict(color=series_color(theme, i), width=2, dash="dash"),
                hovertemplate="%{y:,.2f}",
            ))

    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines", name="Combined" if multi else "P/L at expiry",
        line=dict(color=t["text"], width=3), hovertemplate="%{y:,.2f}",
    ))

    be = [b for b in summary.breakevens if lo <= b <= hi]
    if be:
        fig.add_trace(go.Scatter(
            x=be, y=[0] * len(be), mode="markers", name="Breakeven",
            marker=dict(size=10, symbol="diamond", color=t["text"],
                        line=dict(color=t["surface"], width=2)),
            hovertemplate="Breakeven %{x:,.2f}<extra></extra>",
        ))

    fig.add_hline(y=0, line=dict(color=t["muted"], width=1))
    fig.add_vline(
        x=spot, line=dict(color=t["text2"], width=1.5, dash="dot"),
        annotation=dict(text=f"Spot {spot:,.2f}", font=dict(color=t["text2"]),
                        yanchor="top"),
        annotation_position="top right",
    )

    fig.update_layout(**base_layout(theme, title if show_title else None,
                                    _subtitle(legs) if show_subtitle else None))
    fig.update_layout(
        hovermode="x unified",
        showlegend=multi,
        xaxis_title="Underlying price at expiry",
        yaxis_title="Profit / loss",
        xaxis_hoverformat=",.2f",
    )
    return fig


def single_plotter(
    op_type="c",
    spot=100,
    spot_range=10,
    strike=102,
    tr_type="b",
    op_pr=2,
    contracts=1,
    save=False,
    file="fig.html",
    show=False,
    theme=None,
    show_title=True,
    show_subtitle=True,
    show_toolbar=True,
):
    """Payoff diagram for a single option.

    Parameters
    ----------
    op_type : {'c', 'p'}, default 'c'
        Call or put.
    spot : float, default 100
        Current underlying price.
    spot_range : float, default 10
        Plotted price range, +/- percent around ``spot``.
    strike : float, default 102
        Strike price.
    tr_type : {'b', 's'}, default 'b'
        Long ('b') or short ('s').
    op_pr : float, default 2
        Option premium.
    contracts : float, default 1
        Number of contracts.
    save : bool, default False
        Write the figure to ``file`` (``.html``, or ``.png``/``.svg``/``.pdf``
        with kaleido installed).
    file : str, default 'fig.html'
    show : bool, default False
        Call ``fig.show()``. In Jupyter, the returned figure renders on its own.
    theme : {'light', 'dark'}, optional
        Defaults to the session theme, 'dark' unless changed with
        :func:`opstrat.set_theme`.
    show_title, show_subtitle, show_toolbar : bool, default True
        Set False to hide the chart title, the max profit / max loss /
        breakeven subtitle, or the Plotly toolbar (modebar).

    Returns
    -------
    plotly.graph_objects.Figure

    Example
    -------
    >>> import opstrat as op
    >>> op.single_plotter(op_type='p', spot_range=20, spot=1000, strike=950)
    """
    leg = Leg(op_type, strike, tr_type, op_pr, contracts)
    title = f"{NAMES[leg.tr_type]} {NAMES[leg.op_type]}  ·  Strike {strike:,g}"
    fig = payoff_figure([leg], spot, spot_range, title=title, theme=theme,
                        show_title=show_title, show_subtitle=show_subtitle,
                        show_toolbar=show_toolbar)
    return finish(fig, save, file, show)


def multi_plotter(
    spot_range=20,
    spot=100,
    op_list=DEFAULT_LEGS,
    save=False,
    file="fig.html",
    show=False,
    theme=None,
    title="Multiple options strategy",
    show_legs=True,
    show_title=True,
    show_subtitle=True,
    show_toolbar=True,
):
    """Payoff diagram for several options plus the combined position.

    ``op_list`` is a list of :class:`opstrat.Leg` objects or dicts with keys
    ``op_type`` ('c'/'p'), ``strike``, ``tr_type`` ('b'/'s'), ``op_pr`` and
    optional ``contracts`` (``contract`` also accepted). Display options are as
    in :func:`single_plotter`.

    Example
    -------
    >>> op1 = {'op_type': 'c', 'strike': 110, 'tr_type': 's', 'op_pr': 2}
    >>> op2 = {'op_type': 'p', 'strike': 95, 'tr_type': 's', 'op_pr': 6}
    >>> op.multi_plotter(spot=100, spot_range=20, op_list=[op1, op2])
    """
    fig = payoff_figure(op_list, spot, spot_range, title=title, theme=theme,
                        show_legs=show_legs, show_title=show_title,
                        show_subtitle=show_subtitle, show_toolbar=show_toolbar)
    return finish(fig, save, file, show)


_GREEK_LABELS = {
    "value": "Option value",
    "intrinsic": "Intrinsic value",
    "time_value": "Time value",
    "delta": "Delta",
    "gamma": "Gamma",
    "theta": "Theta (per day)",
    "vega": "Vega (per 1 vol pt)",
    "rho": "Rho (per 1 rate pt)",
}


def _pick(res: dict, name: str):
    if name == "value":
        return res["value"]["option value"]
    if name == "intrinsic":
        return res["value"]["intrinsic value"]
    if name == "time_value":
        return res["value"]["time value"]
    return res["greeks"][name]


def greeks_plotter(
    K=100,
    St=95,
    t=30,
    r=4,
    v: float | Sequence[float] = (10, 25, 40, 60),
    type="c",
    q=0.0,
    x_axis="t",
    x_range=None,
    greeks=("value", "delta", "gamma", "theta", "vega", "rho"),
    save=False,
    file="greeks.html",
    show=False,
    theme=None,
    show_title=True,
    show_toolbar=True,
):
    """Plot Black-Scholes value and greeks, one panel per measure.

    Each volatility in ``v`` is drawn as its own series.

    Parameters
    ----------
    x_axis : {'t', 'spot'}
        ``'t'``: x is days to expiry (0.5..``x_range``, default 100), counting
        down toward expiry; ``St`` is held fixed.
        ``'spot'``: x is the underlying price within +/- ``x_range`` percent
        (default 30) of ``K``; ``t`` is held fixed.
    greeks : sequence of str
        Any of 'value', 'intrinsic', 'time_value', 'delta', 'gamma',
        'theta', 'vega', 'rho'.
    show_title, show_toolbar : bool, default True
        Set False to hide the chart title or the Plotly toolbar.

    Example
    -------
    >>> op.greeks_plotter(K=100, St=95, v=[20, 40], x_axis='t')
    """
    unknown = set(greeks) - set(_GREEK_LABELS)
    if unknown:
        raise ValueError(f"Unknown greek(s): {sorted(unknown)}")
    vols = [v] if np.isscalar(v) else list(v)
    theme = resolve_theme(theme)
    t_ = tokens(theme)

    if x_axis == "t":
        x = np.linspace(0.5, x_range or 100, 400)
        kwargs = dict(t=x, St=St)
        x_title = "Days to expiry"
        title = f"{NAMES[type.lower()]} greeks vs time  ·  K={K:g}, S={St:g}"
    elif x_axis == "spot":
        pct = x_range or 30
        x = np.linspace(K * (1 - pct / 100), K * (1 + pct / 100), 401)
        kwargs = dict(t=t, St=x)
        x_title = "Underlying price"
        title = f"{NAMES[type.lower()]} greeks vs price  ·  K={K:g}, {t:g} days"
    else:
        raise ValueError("x_axis must be 't' or 'spot'")

    cols = 2 if len(greeks) > 1 else 1
    rows = -(-len(greeks) // cols)
    fig = make_subplots(rows=rows, cols=cols, shared_xaxes=True,
                        figure=OpstratFigure(plotly_config=toolbar_config(show_toolbar)),
                        subplot_titles=[_GREEK_LABELS[g] for g in greeks],
                        vertical_spacing=0.09, horizontal_spacing=0.08)

    for i, vol in enumerate(vols):
        res = black_scholes(K=K, r=r, v=vol, type=type, q=q, **kwargs)
        color = series_color(theme, i)
        for j, g in enumerate(greeks):
            fig.add_trace(go.Scatter(
                x=x, y=_pick(res, g), mode="lines", name=f"σ = {vol:g}%",
                legendgroup=str(vol), showlegend=(j == 0),
                line=dict(color=color, width=2),
                hovertemplate=f"σ {vol:g}%: %{{y:,.4f}}<extra></extra>",
            ), row=j // cols + 1, col=j % cols + 1)

    layout = base_layout(theme, title if show_title else None)
    axis = layout.pop("xaxis")
    layout.pop("yaxis")
    fig.update_layout(**layout)
    height = 280 * rows + 120
    plot_h = height - layout["margin"]["t"] - layout["margin"]["b"]
    fig.update_layout(height=height, hovermode="x unified",
                      legend_y=1 + 30 / plot_h)
    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)
    fig.update_xaxes(title_text=x_title, row=rows)
    if x_axis == "t":
        fig.update_xaxes(autorange="reversed")
    else:
        fig.add_vline(x=K, line=dict(color=t_["muted"], width=1, dash="dot"))
    fig.update_annotations(font=dict(color=t_["text2"], size=13))
    return finish(fig, save, file, show)
