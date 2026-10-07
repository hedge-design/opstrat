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


def tokens(theme: str) -> dict:
    if theme not in _TOKENS:
        raise ValueError("theme must be 'light' or 'dark'")
    return {**_TOKENS[theme], "series": _SERIES[theme]}


def series_color(theme: str, i: int) -> str:
    palette = _SERIES[theme]
    if i >= len(palette):
        raise ValueError(f"At most {len(palette)} series can be plotted on one chart")
    return palette[i]


def base_layout(theme: str, title: str, subtitle: str | None = None) -> dict:
    t = tokens(theme)
    axis = dict(gridcolor=t["grid"], zeroline=False, linecolor=t["grid"],
                tickfont=dict(color=t["text2"]), title_font=dict(color=t["text2"]))
    return dict(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=18, color=t["text"]),
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
        margin=dict(l=60, r=30, t=110, b=60),
        height=520,
    )


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
