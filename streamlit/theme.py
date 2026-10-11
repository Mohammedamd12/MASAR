"""Colours, chart styling and small HTML pieces for the Masar dashboard.

Palette from the project proposal: dark brown surfaces, cream text, terracotta accent.
Series colours were checked for colour-blind safety and contrast on the brown surface.
"""
from __future__ import annotations

import html

import plotly.graph_objects as go

# Surfaces & ink (proposal)
BG = "#241b12"
CARD = "#2e2318"
CARD_BORDER = "rgba(236,237,224,0.09)"
CREAM = "#ecede0"
MUTED = "#b4a996"
FAINT = "rgba(236,237,224,0.08)"
ACCENT = "#c98a68"          # terracotta (single-series bars, highlights)
NEUTRAL_MID = "#3e352b"     # diverging midpoint
LAND = "#3a2d20"            # map land
SEA = "#1b140d"             # map sea
BORDER = "#5a4836"          # map borders

# Categorical — colour follows the entity: a region keeps its colour whatever the filters.
REGION_COLORS = {
    "Riyadh": "#d95926",
    "Eastern": "#3987e5",
    "Makkah": "#199e70",
    "Qassim": "#c98500",
    "Tabuk": "#d55181",
}
ENTRIES = "#3987e5"
EXITS = "#d95926"
UP = "#3987e5"              # diverging: growth up
DOWN = "#e66767"            # diverging: growth down

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'

CSS = f"""
<style>
.block-container {{ padding-top: 1.6rem; padding-bottom: 2rem; max-width: 1400px; }}
.masar-eyebrow {{ color: {ACCENT}; font-size: .78rem; letter-spacing: .14em; text-transform: uppercase;
                  font-weight: 600; margin-bottom: .1rem; }}
.masar-title {{ color: {CREAM}; font-size: 2.1rem; font-weight: 700; line-height: 1.15; margin: 0; }}
.masar-sub {{ color: {MUTED}; font-size: .95rem; margin-top: .25rem; }}
.masar-pill {{ display: inline-block; padding: .25rem .7rem; border-radius: 999px; font-size: .78rem;
               border: 1px solid {CARD_BORDER}; background: {CARD}; color: {MUTED}; margin: .55rem .4rem 0 0; }}
.masar-pill b {{ color: {CREAM}; font-weight: 600; }}
.kpi {{ background: {CARD}; border: 1px solid {CARD_BORDER}; border-radius: 14px; padding: .9rem 1rem;
        min-height: 150px; }}
.kpi-label {{ color: {MUTED}; font-size: .7rem; letter-spacing: .1em; text-transform: uppercase;
              font-weight: 600; }}
.kpi-value {{ color: {CREAM}; font-size: 1.65rem; font-weight: 700; margin-top: .2rem; line-height: 1.2;
              overflow-wrap: anywhere; }}
.kpi-sub {{ color: {MUTED}; font-size: .78rem; margin-top: .2rem; }}
.ctx-row {{ display: flex; gap: .75rem; align-items: flex-start; padding: .55rem 0;
            border-bottom: 1px solid {FAINT}; }}
.ctx-row:last-child {{ border-bottom: none; }}
.ctx-icon {{ width: 30px; height: 30px; border-radius: 8px; background: {BG}; display: flex;
             align-items: center; justify-content: center; flex-shrink: 0; font-size: .95rem; }}
.ctx-main {{ color: {CREAM}; font-weight: 600; font-size: .95rem; }}
.ctx-note {{ color: {MUTED}; font-size: .78rem; }}
.masar-note {{ color: {MUTED}; font-size: .8rem; }}
div[data-testid="stVerticalBlockBorderWrapper"] {{ background: {CARD}; border-radius: 14px; }}
</style>
"""


def kpi(label: str, value: str, sub: str = "") -> str:
    return (f'<div class="kpi"><div class="kpi-label">{html.escape(label)}</div>'
            f'<div class="kpi-value">{html.escape(value)}</div>'
            f'<div class="kpi-sub">{html.escape(sub)}</div></div>')


def ctx_row(icon: str, main: str, note: str) -> str:
    return (f'<div class="ctx-row"><div class="ctx-icon">{icon}</div><div>'
            f'<div class="ctx-main">{html.escape(main)}</div>'
            f'<div class="ctx-note">{html.escape(note)}</div></div></div>')


def pill(label: str, value: str) -> str:
    return f'<span class="masar-pill">{html.escape(label)} <b>{html.escape(value)}</b></span>'


def style(fig: go.Figure, height: int = 360, title: str | None = None) -> go.Figure:
    """Quiet chart chrome on the brown surface."""
    fig.update_layout(
        height=height,
        title=dict(text=title, font=dict(size=15, color=CREAM), x=0, xanchor="left") if title else None,
        margin=dict(l=4, r=12, t=44 if title else 12, b=4),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=MUTED, size=12),
        legend=dict(orientation="h", yanchor="top", y=-0.08, x=0, title=None,
                    font=dict(color=CREAM), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=BG, bordercolor=CARD_BORDER, font=dict(color=CREAM, size=13)),
    )
    fig.update_xaxes(showgrid=False, title=None, linecolor=FAINT, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=FAINT, title=None, zeroline=False, tickfont=dict(color=MUTED))
    return fig