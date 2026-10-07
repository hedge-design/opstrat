import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest
from scipy.stats import norm

import opstrat as op
from opstrat.helpers import payoff_calculator


# ---------------------------------------------------------------- payoff


def legacy_payoff(x, op_type, strike, op_pr, tr_type, n):
    """The pre-1.0 loop implementation, for regression comparison."""
    if op_type == "c":
        y = np.array([max(xi - strike - op_pr, -op_pr) for xi in x])
    else:
        y = np.array([max(strike - xi - op_pr, -op_pr) for xi in x])
    return (-y if tr_type == "s" else y) * n


@pytest.mark.parametrize("op_type", ["c", "p"])
@pytest.mark.parametrize("tr_type", ["b", "s"])
def test_payoff_matches_legacy(op_type, tr_type):
    x = np.linspace(50, 150, 501)
    np.testing.assert_allclose(
        payoff_calculator(x, op_type, 100, 3.5, tr_type, 2),
        legacy_payoff(x, op_type, 100, 3.5, tr_type, 2),
    )


def test_leg_validation_and_legacy_contract_key():
    with pytest.raises(ValueError):
        op.Leg("x", 100)
    with pytest.raises(ValueError):
        op.Leg("c", 100, "z")
    leg = op.Leg.from_dict({"op_type": "C", "strike": 100, "tr_type": "S", "contract": 3})
    assert (leg.op_type, leg.tr_type, leg.contracts) == ("c", "s", 3)


def test_summary_short_strangle():
    legs = [
        {"op_type": "c", "strike": 110, "tr_type": "s", "op_pr": 2},
        {"op_type": "p", "strike": 95, "tr_type": "s", "op_pr": 6},
    ]
    s = op.summarize(legs)
    assert s.breakevens == pytest.approx((87.0, 118.0))
    assert s.max_profit == pytest.approx(8.0)
    assert s.max_loss == -math.inf  # short call: unlimited upside loss
    assert s.net_premium == pytest.approx(8.0)


def test_summary_iron_condor_bounded():
    legs = [
        {"op_type": "c", "strike": 215, "tr_type": "s", "op_pr": 7.63},
        {"op_type": "c", "strike": 220, "tr_type": "b", "op_pr": 5.35},
        {"op_type": "p", "strike": 210, "tr_type": "s", "op_pr": 7.20},
        {"op_type": "p", "strike": 205, "tr_type": "b", "op_pr": 5.52},
    ]
    s = op.summarize(legs)
    credit = 7.63 - 5.35 + 7.20 - 5.52
    assert s.max_profit == pytest.approx(credit)
    assert s.max_loss == pytest.approx(credit - 5)
    assert s.breakevens == pytest.approx((210 - credit, 215 + credit))


def test_summary_long_call():
    s = op.summarize([op.Leg("c", 100, "b", 5)])
    assert s.max_profit == math.inf
    assert s.max_loss == pytest.approx(-5)
    assert s.breakevens == pytest.approx((105,))


# ---------------------------------------------------------- black-scholes


def legacy_bs(t, r, v, K, St, type):
    t, r, v = t / 365, r / 100, v / 100
    d1 = (np.log(St / K) + (r + v**2 / 2) * t) / (v * np.sqrt(t))
    d2 = d1 - v * np.sqrt(t)
    if type == "c":
        val = St * norm.cdf(d1) - K * np.exp(-r * t) * norm.cdf(d2)
        delta = norm.cdf(d1)
    else:
        val = K * np.exp(-r * t) * norm.cdf(-d2) - St * norm.cdf(-d1)
        delta = -norm.cdf(-d1)
    return val, delta


@pytest.mark.parametrize("type", ["c", "p"])
def test_black_scholes_scalar_matches_legacy(type):
    res = op.black_scholes(t=30, r=4, v=20, K=200, St=208, type=type)
    val, delta = legacy_bs(30, 4, 20, 200, 208, type)
    assert isinstance(res["value"]["option value"], float)
    assert res["value"]["option value"] == pytest.approx(val)
    assert res["greeks"]["delta"] == pytest.approx(delta)


def test_black_scholes_put_call_parity_and_vectorised():
    St = np.linspace(80, 120, 9)
    c = op.black_scholes(t=60, r=5, v=30, K=100, St=St, type="c", q=1)
    p = op.black_scholes(t=60, r=5, v=30, K=100, St=St, type="p", q=1)
    T = 60 / 365
    lhs = c["value"]["option value"] - p["value"]["option value"]
    rhs = St * np.exp(-0.01 * T) - 100 * np.exp(-0.05 * T)
    np.testing.assert_allclose(lhs, rhs, atol=1e-10)
    assert c["greeks"]["gamma"].shape == St.shape


def test_black_scholes_greeks_match_finite_differences():
    base = dict(t=45, r=3, v=25, K=100, St=102, type="c")
    g = op.black_scholes(**base)["greeks"]
    price = lambda **kw: op.black_scholes(**{**base, **kw})["value"]["option value"]
    h = 1e-3
    assert g["delta"] == pytest.approx((price(St=102 + h) - price(St=102 - h)) / (2 * h), rel=1e-5)
    assert g["vega"] == pytest.approx((price(v=25 + h) - price(v=25 - h)) / (2 * h), rel=1e-5)
    assert g["rho"] == pytest.approx((price(r=3 + h) - price(r=3 - h)) / (2 * h), rel=1e-5)
    assert g["theta"] == pytest.approx(-(price(t=45 + h) - price(t=45 - h)) / (2 * h), rel=1e-4)


def test_black_scholes_at_expiry_is_intrinsic():
    res = op.black_scholes(t=0, K=100, St=110, type="c")
    assert res["value"]["option value"] == pytest.approx(10)
    assert res["greeks"]["delta"] == 1.0


# -------------------------------------------------------------- plotting


def test_single_plotter_returns_figure():
    fig = op.single_plotter(spot=460, strike=460, op_type="p", tr_type="s", op_pr=12.5)
    assert isinstance(fig, go.Figure)
    assert "Breakeven" in [t.name for t in fig.data]
    assert "Max profit 12.50" in fig.layout.title.subtitle.text


def test_multi_plotter_traces_and_save(tmp_path):
    out = tmp_path / "strategy.html"
    fig = op.multi_plotter(save=True, file=str(out), theme="dark")
    names = [t.name for t in fig.data]
    assert "Combined" in names and sum("Short" in n for n in names) == 2
    assert out.exists() and out.stat().st_size > 0


def test_payoff_figure_exact_breakevens_in_grid():
    fig = op.payoff_figure([op.Leg("c", 100, "b", 5)], spot=100, spot_range=20)
    combined = next(t for t in fig.data if t.name == "P/L at expiry")
    assert 105.0 in set(np.round(combined.x, 10))


def test_greeks_plotter_panels():
    fig = op.greeks_plotter(v=[20, 40], greeks=("delta", "gamma", "theta"))
    assert len(fig.data) == 6
    assert fig.layout.xaxis.autorange == "reversed"
    fig2 = op.greeks_plotter(v=30, x_axis="spot", greeks=("value",))
    assert len(fig2.data) == 1
    with pytest.raises(ValueError):
        op.greeks_plotter(greeks=("charm",))


# --------------------------------------------------------------- yfinance


class _Chain:
    def __init__(self):
        self.calls = pd.DataFrame(
            {"strike": [95.0, 100.0, 105.0], "lastPrice": [7.0, 4.0, 2.0],
             "bid": [6.8, 3.9, 0.0], "ask": [7.2, 4.1, 0.0]})
        self.puts = pd.DataFrame(
            {"strike": [95.0, 100.0, 105.0], "lastPrice": [1.5, 3.0, 6.0],
             "bid": [1.4, 2.9, 5.8], "ask": [1.6, 3.1, 6.2]})


class _Ticker:
    def __init__(self, sym):
        self.fast_info = {"lastPrice": 100.0}
        self.info = {}
        self.options = ("2026-10-16", "2026-10-23")

    def option_chain(self, exp):
        return _Chain()


@pytest.fixture
def fake_yf(monkeypatch):
    import types

    import opstrat.yf as yfmod

    monkeypatch.setattr(yfmod, "_yf", lambda: types.SimpleNamespace(Ticker=_Ticker))


def test_yf_plotter_prices_from_chain(fake_yf):
    legs = [{"op_type": "c", "strike": 100, "tr_type": "b"},
            {"op_type": "p", "strike": 100, "tr_type": "b"}]
    fig = op.yf_plotter("abc", op_list=legs, price="mid")
    assert "Exp 2026-10-16" in fig.layout.title.text
    # long straddle at 100 for 4.0 + 3.0 mid premiums -> breakevens 93 / 107
    assert "93.00, 107.00" in fig.layout.title.subtitle.text


def test_yf_plotter_bad_strike_and_expiry(fake_yf):
    with pytest.raises(ValueError, match="Nearest"):
        op.yf_plotter("abc", op_list=[{"op_type": "c", "strike": 101, "tr_type": "b"}])
    with pytest.raises(ValueError, match="not available"):
        op.yf_plotter("abc", exp="2030-01-01", op_list=[{"op_type": "c", "strike": 100}])


def test_dark_is_default_and_set_theme():
    dark_bg = op.multi_plotter().layout.paper_bgcolor
    assert op.get_theme() == "dark" and dark_bg == "#1a1a19"
    try:
        op.set_theme("light")
        assert op.single_plotter().layout.paper_bgcolor == "#fcfcfb"
        assert op.greeks_plotter(v=20, greeks=("delta",)).layout.paper_bgcolor == "#fcfcfb"
        assert op.single_plotter(theme="dark").layout.paper_bgcolor == dark_bg  # per-call override
        with pytest.raises(ValueError):
            op.set_theme("blue")
    finally:
        op.set_theme("dark")


def test_title_subtitle_toolbar_on_by_default():
    fig = op.multi_plotter()
    assert fig.layout.title.text and fig.layout.title.subtitle.text
    assert fig.plotly_config == {}
    assert isinstance(fig, go.Figure)


def test_hide_title_subtitle_toolbar(tmp_path):
    fig = op.single_plotter(show_title=False, show_subtitle=False, show_toolbar=False)
    assert fig.layout.title.text == "" and fig.layout.title.subtitle.text == ""
    assert fig.layout.margin.t < op.single_plotter().layout.margin.t
    assert fig.plotly_config == {"displayModeBar": False}

    # toolbar setting reaches saved HTML
    out = tmp_path / "f.html"
    op.multi_plotter(show_toolbar=False, save=True, file=str(out))
    assert '"displayModeBar": false' in out.read_text()

    g = op.greeks_plotter(v=20, greeks=("delta",), show_title=False, show_toolbar=False)
    assert g.layout.title.text == "" and g.plotly_config == {"displayModeBar": False}


def test_toolbar_config_in_mimebundle():
    import plotly.io as pio

    old = pio.renderers.default
    try:
        pio.renderers.default = "plotly_mimetype"
        bundle = op.multi_plotter(show_toolbar=False)._repr_mimebundle_()
        assert bundle["application/vnd.plotly.v1+json"]["config"]["displayModeBar"] is False
    finally:
        pio.renderers.default = old
