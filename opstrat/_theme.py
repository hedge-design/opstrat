"""Shared Plotly styling and figure output helpers."""

from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go

# Colour-vision-deficiency-validated categorical order (light / dark steps).
_SERIES = {
    "light": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
              "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
    "dark": ["#3987e5", "#d95926", "#199e70", "#c98500",
             "#d55181", "#008300", "#9085e9", "#e66767"],
}

_TOKENS = {
    "light": dict(surface="#fcfcfb", text="#0b0b0b", text2="#52514e", muted="#8a8984",
                  grid="#e6e5e1", profit="rgba(42,120,214,0.16)", loss="rgba(227,73,72,0.16)"),
    "dark": dict(surface="#1a1a19", text="#ffffff", text2="#c3c2b7", muted="#8f8e88",
                 grid="#33332f", profit="rgba(57,135,229,0.22)", loss="rgba(230,103,103,0.22)"),
}


_default_theme = "dark"


def set_theme(theme: str) -> None:
    """Set the theme used when a plotter is called without ``theme=``.

    >>> op.set_theme('light')
    """
    global _default_theme
    _default_theme = resolve_theme(theme)


def get_theme() -> str:
    """Return the current default theme."""
    return _default_theme


def resolve_theme(theme: str | None) -> str:
    theme = _default_theme if theme is None else str(theme).lower()
    if theme not in _TOKENS:
        raise ValueError("theme must be 'light' or 'dark'")
    return theme


def tokens(theme: str) -> dict:
    if theme not in _TOKENS:
        raise ValueError("theme must be 'light' or 'dark'")
    return {**_TOKENS[theme], "series": _SERIES[theme]}


def series_color(theme: str, i: int) -> str:
    palette = _SERIES[theme]
    if i >= len(palette):
        raise ValueError(f"At most {len(palette)} series can be plotted on one chart")
    return palette[i]


def base_layout(theme: str, title: str | None, subtitle: str | None = None) -> dict:
    """Layout shared by all charts. ``None`` title/subtitle hides it and
    shrinks the top margin to match."""
    t = tokens(theme)
    axis = dict(gridcolor=t["grid"], zeroline=False, linecolor=t["grid"],
                tickfont=dict(color=t["text2"]), title_font=dict(color=t["text2"]))
    top = 40 + (40 if title else 0) + (30 if subtitle else 0)
    return dict(
        title=dict(text=title or "", x=0, xanchor="left", font=dict(size=18, color=t["text"]),
                   subtitle=dict(text=subtitle or "", font=dict(size=13, color=t["text2"]))),
        paper_bgcolor=t["surface"],
        plot_bgcolor=t["surface"],
        font=dict(family="Inter, system-ui, -apple-system, Segoe UI, sans-serif",
                  color=t["text"]),
        xaxis=axis,
        yaxis=axis,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0,
                    font=dict(color=t["text2"]), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=t["surface"], font=dict(color=t["text"]),
                        bordercolor=t["grid"]),
        modebar=dict(bgcolor="rgba(0,0,0,0)", color=t["muted"], activecolor=t["text"]),
        margin=dict(l=60, r=30, t=top, b=60),
        height=520,
    )


class OpstratFigure(go.Figure):
    """A ``go.Figure`` that remembers its Plotly display config.

    The config (e.g. ``{'displayModeBar': False}`` to hide the toolbar) is
    applied in notebooks, ``show()``, ``to_html()`` and ``write_html()``.
    A ``config=`` passed to those calls is merged on top.
    """

    def __init__(self, *args, plotly_config: dict | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._plotly_config = dict(plotly_config or {})

    @property
    def plotly_config(self) -> dict:
        return self._plotly_config

    @plotly_config.setter
    def plotly_config(self, value: dict) -> None:
        self._plotly_config = dict(value or {})

    def _with_config(self, kwargs: dict) -> dict:
        return {**kwargs, "config": {**self._plotly_config, **(kwargs.get("config") or {})}}

    def show(self, *args, **kwargs):
        return super().show(*args, **self._with_config(kwargs))

    def to_html(self, *args, **kwargs):
        return super().to_html(*args, **self._with_config(kwargs))

    def write_html(self, *args, **kwargs):
        return super().write_html(*args, **self._with_config(kwargs))

    def _repr_mimebundle_(self, include=None, exclude=None, validate=True, **kwargs):
        return super()._repr_mimebundle_(include, exclude, validate, **self._with_config(kwargs))

    def _ipython_display_(self):
        import plotly.io as pio

        if pio.renderers.render_on_display and pio.renderers.default:
            self.show()
        else:
            print(repr(self))


def toolbar_config(show_toolbar: bool) -> dict:
    return {} if show_toolbar else {"displayModeBar": False}


def finish(fig: go.Figure, save: bool, file: str | Path, show: bool) -> go.Figure:
    """Optionally save and/or display the figure, then return it."""
    if save:
        path = Path(file)
        if path.suffix.lower() in (".html", ".htm"):
            fig.write_html(path, include_plotlyjs="cdn")
        else:
            try:
                fig.write_image(path)
            except (ValueError, ImportError, RuntimeError) as e:
                raise RuntimeError(
                    f"Saving to {path.suffix or 'an image'} needs the 'kaleido' package "
                    "(pip install 'opstrat[image]'), or save as .html instead."
                ) from e
    if show:
        fig.show()
    return fig
