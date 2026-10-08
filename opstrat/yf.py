"""Payoff plots priced from live Yahoo Finance option chains."""

from __future__ import annotations

from collections.abc import Mapping

from ._theme import finish
from .legs import Leg, check_optype, check_trtype
from .plotting import payoff_figure

DEFAULT_YF_LEGS = (
    {"op_type": "c", "strike": 300, "tr_type": "b", "contracts": 1},
    {"op_type": "p", "strike": 280, "tr_type": "b", "contracts": 1},
)


def _yf():
    try:
        import yfinance
    except ImportError as e:
        raise ImportError(
            "yf_plotter needs yfinance: pip install 'opstrat[yf]'"
        ) from e
    return yfinance


def spot_price(ticker: str) -> float:
    """Latest traded price of ``ticker`` from Yahoo Finance."""
    tk = _yf().Ticker(ticker)
    try:
        price = tk.fast_info["lastPrice"]
    except Exception:
        price = None
    if not price:
        price = (tk.info or {}).get("currentPrice") or (tk.info or {}).get(
            "regularMarketPrice"
        )
    if not price:
        raise ValueError(f"Ticker {ticker!r} not recognized")
    return float(price)


def _option_price(row, price: str) -> float:
    if price == "mid":
        bid, ask = float(row["bid"]), float(row["ask"])
        if bid > 0 and ask > 0:
            return (bid + ask) / 2
    elif price in ("bid", "ask"):
        p = float(row[price])
        if p > 0:
            return p
    return float(row["lastPrice"])


def yf_plotter(
    ticker="msft",
    exp="default",
    spot_range=10,
    op_list=DEFAULT_YF_LEGS,
    price="last",
    save=False,
    file="fig.html",
    show=False,
    theme=None,
    show_title=True,
    show_subtitle=True,
    show_toolbar=True,
):
    """Payoff diagram using current option prices from Yahoo Finance.

    Parameters
    ----------
    ticker : str, default 'msft'
    exp : str, default 'default'
        Expiration as 'YYYY-MM-DD'; 'default' uses the nearest expiry.
    spot_range : float, default 10
        Plotted range, +/- percent around the current price.
    op_list : list of dict or Leg
        Each needs ``op_type``, ``strike``, ``tr_type`` and optionally
        ``contracts``. Any ``op_pr`` given is replaced by the market price.
    price : {'last', 'mid', 'bid', 'ask'}, default 'last'
        Which quote to use as the premium. Falls back to the last trade
        price when the quote is zero (e.g. outside market hours).

    Other display options (``theme``, ``show_title``, ``show_subtitle``,
    ``show_toolbar``, ``save``, ``file``, ``show``) are as in
    :func:`opstrat.single_plotter`.

    Example
    -------
    >>> op1 = {'op_type': 'c', 'strike': 250, 'tr_type': 'b'}
    >>> op2 = {'op_type': 'p', 'strike': 225, 'tr_type': 'b', 'contracts': 3}
    >>> op.yf_plotter(ticker='msft', exp='default', op_list=[op1, op2])
    """
    if price not in ("last", "mid", "bid", "ask"):
        raise ValueError("price must be 'last', 'mid', 'bid' or 'ask'")
    tk = _yf().Ticker(ticker)
    spot = spot_price(ticker)

    expiries = tk.options
    if not expiries:
        raise ValueError(f"No listed options for {ticker!r}")
    if exp == "default":
        exp = expiries[0]
    elif exp not in expiries:
        raise ValueError(
            f"Option for the given date not available! Choose from: {', '.join(expiries[:8])}…"
        )

    chain = tk.option_chain(exp)
    legs = []
    for op in op_list:
        if isinstance(op, Leg):
            op = {"op_type": op.op_type, "strike": op.strike,
                  "tr_type": op.tr_type, "contracts": op.contracts}
        elif not isinstance(op, Mapping):
            raise TypeError("op_list items must be dicts or Leg objects")
        op_type = check_optype(op["op_type"])
        check_trtype(op.get("tr_type", "b"))
        df = chain.calls if op_type == "c" else chain.puts
        match = df[df["strike"] == float(op["strike"])]
        if match.empty:
            near = df["strike"].iloc[(df["strike"] - float(op["strike"])).abs().argsort()[:5]]
            raise ValueError(
                f"Option for strike {op['strike']} not available! Nearest: "
                + ", ".join(f"{s:g}" for s in sorted(near))
            )
        legs.append(Leg.from_dict({**op, "op_pr": _option_price(match.iloc[0], price)}))

    title = f"{ticker.upper()} option strategy  ·  Exp {exp}"
    fig = payoff_figure(legs, spot, spot_range, title=title, theme=theme,
                        show_title=show_title, show_subtitle=show_subtitle,
                        show_toolbar=show_toolbar)
    return finish(fig, save, file, show)
