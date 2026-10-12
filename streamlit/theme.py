"""Colours, chart styling and HTML pieces for the Masar dashboard.

Palette from the MASAR progress-update deck: navy surfaces, sky → teal → green route gradient.
Cards are a step lighter than the deck so they separate clearly from the page.
"""
from __future__ import annotations

import base64
import html
import re
from pathlib import Path

import plotly.graph_objects as go

ASSETS = Path(__file__).resolve().parent / "assets"

# --------------------------------------------------------------------------- palette
BG = "#0a1430"               # page
CARD = "#152a56"             # cards / tiles (a touch lighter than the deck for contrast)
CARD_2 = "#10224a"           # inner surfaces (sidebar, inputs)
LINE = "#2a4478"             # borders / dividers
TXT = "#e6f2f7"              # primary text
MUTED = "#a6b3cf"            # secondary text (lighter than the deck's #8a97b5 for legibility)
FAINT = "rgba(166,179,207,0.14)"
SKY, TEAL, GREEN = "#5fd3e0", "#1ec6cf", "#2dd68c"
ACCENT = TEAL                # single-series bars, highlights
WARN = "#f59e0b"             # warning cards (orange border)
LAND, SEA, BORDER = "#1a3263", "#0a1430", "#36548e"
NEUTRAL_MID = "#1d3260"      # diverging midpoint

# Categorical — colour follows the entity: a region keeps its colour whatever the filters.
REGION_COLORS = {
    "Riyadh": "#5fd3e0",
    "Eastern": "#2dd68c",
    "Makkah": "#f4a259",
    "Qassim": "#b79cff",
    "Tabuk": "#ff7a9a",
}
ENTRIES = SKY
EXITS = "#f4a259"
UP = GREEN                   # diverging: growth up
DOWN = "#ff6b6b"             # diverging: growth down

FONT = 'Montserrat, "Segoe UI", system-ui, sans-serif'
FONT_AR = 'Cairo, "Segoe UI", sans-serif'


def _asset(name: str) -> str:
    try:
        return (ASSETS / name).read_text(encoding="utf-8")
    except OSError:
        return ""


def _b64(name: str) -> str:
    try:
        return base64.b64encode((ASSETS / name).read_bytes()).decode()
    except OSError:
        return ""


ICON_SVG = _asset("masar_icon.svg")
WORDMARK = _b64("masar_wordmark.png")
FAVICON = str(ASSETS / "favicon.png") if (ASSETS / "favicon.png").exists() else "🧭"


def _flat(s: str) -> str:
    """Streamlit's markdown turns blank lines / indented lines into paragraphs or code: keep HTML on one line."""
    return re.sub(r"\s*\n\s*", " ", s).strip()


def esc(s) -> str:
    return html.escape(str(s))


# --------------------------------------------------------------------------- page CSS
CSS = _flat(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700&family=Cairo:wght@600;700&display=swap');
html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"], .stMarkdown, button, input, textarea {{
  font-family: {FONT}; }}
[data-testid="stAppViewContainer"] {{ background: {BG}; }}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 1.4rem; padding-bottom: 1.5rem; max-width: 1440px; }}
[data-testid="stSidebar"] {{ background: {CARD_2}; border-right: 1px solid {LINE}; }}
[data-testid="stSidebar"] h3 {{ font-size: .78rem; letter-spacing: .16em; text-transform: uppercase; color: {MUTED}; }}
p, li, label, .stCaption, [data-testid="stCaptionContainer"] {{ color: {MUTED}; }}
h1, h2, h3, h4, h5 {{ color: {TXT}; font-family: {FONT}; }}

/* bordered containers = cards */
div[data-testid="stVerticalBlockBorderWrapper"] {{ background: {CARD}; border: 1px solid {LINE} !important;
  border-radius: 14px; }}

/* tabs: active tab is a filled pill */
div[data-baseweb="tab-list"] {{ gap: .35rem; background: {CARD_2}; border: 1px solid {LINE}; border-radius: 999px;
  padding: .3rem; width: fit-content; max-width: 100%; overflow-x: auto; }}
div[data-baseweb="tab-list"] button[role="tab"] {{ border-radius: 999px; padding: .45rem 1rem; height: auto;
  background: transparent; color: {MUTED}; }}
div[data-baseweb="tab-list"] button[role="tab"] p {{ font-weight: 600; font-size: .85rem; color: inherit; }}
div[data-baseweb="tab-list"] button[role="tab"]:hover {{ color: {TXT}; background: rgba(95,211,224,.08); }}
div[data-baseweb="tab-list"] button[role="tab"][aria-selected="true"] {{ background: linear-gradient(90deg,{SKY},{GREEN});
  color: {BG}; }}
div[data-baseweb="tab-highlight"], div[data-baseweb="tab-border"] {{ display: none; }}
div[data-baseweb="tab-panel"] {{ padding-top: 1rem; }}

/* horizontal radios (map colour switch) drawn as a segmented pill */
div[role="radiogroup"][aria-orientation="horizontal"], div[data-testid="stRadio"] div[role="radiogroup"] {{
  display: inline-flex; gap: .25rem; background: {CARD_2}; border: 1px solid {LINE}; border-radius: 999px; padding: .25rem; }}
div[data-testid="stRadio"] label[data-baseweb="radio"] {{ margin: 0; padding: .3rem .9rem; border-radius: 999px; cursor: pointer; }}
div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {{ display: none; }}
div[data-testid="stRadio"] label[data-baseweb="radio"] p {{ font-size: .82rem; font-weight: 600; color: {MUTED}; }}
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {{ background: linear-gradient(90deg, {SKY}, {GREEN}); }}
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p {{ color: {BG}; }}

/* inputs & buttons */
[data-baseweb="select"] > div {{ background: {CARD}; border-color: {LINE}; }}
[data-baseweb="tag"] {{ background: rgba(30,198,207,.18) !important; color: {TXT} !important; }}
.stButton > button, .stDownloadButton > button {{ background: {CARD}; color: {TXT}; border: 1px solid {LINE};
  border-radius: 10px; font-weight: 600; }}
.stButton > button:hover, .stDownloadButton > button:hover {{ border-color: {TEAL}; color: {SKY}; }}
[data-testid="stExpander"] details {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 12px; }}
[data-testid="stDataFrame"] {{ border: 1px solid {LINE}; border-radius: 12px; overflow: hidden; }}

/* header */
.mh {{ container-type: inline-size; position: relative; overflow: hidden; border: 1px solid {LINE}; border-radius: 18px; padding: 22px 26px 22px;
  margin-bottom: 1rem; color: {TXT};
  background: radial-gradient(1200px 260px at 85% -40%, rgba(30,198,207,.18), transparent 60%),
              radial-gradient(600px 200px at 0% 120%, rgba(45,214,140,.10), transparent 60%),
              linear-gradient(180deg, #102048, {BG}); }}
.mh::before {{ content: ""; position: absolute; inset: 0; pointer-events: none;
  background-image: radial-gradient(rgba(166,179,207,.16) 1px, transparent 1px); background-size: 18px 18px;
  mask-image: linear-gradient(90deg, transparent, #000 45%); -webkit-mask-image: linear-gradient(90deg, transparent, #000 45%); }}
.mh::after {{ content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 3px;
  background: linear-gradient(90deg, {SKY}, {TEAL}, {GREEN}); }}
.mh-top {{ position: relative; display: flex; align-items: center; gap: 22px; min-height: 150px; }}
.mh-brand {{ display: flex; align-items: center; gap: 14px; flex: none; }}
.mh-brand .ic {{ width: 78px; height: 78px; }} .mh-brand .ic svg {{ width: 100%; height: 100%; }}
.mh-brand .wm {{ height: 66px; width: auto; }}
.mh-sep {{ width: 1px; align-self: stretch; margin: 14px 4px; background: linear-gradient(180deg, transparent, {LINE}, transparent); }}
.mh-title {{ flex: none; max-width: 560px; position: relative; z-index: 1; }}
.mh-eyebrow {{ font-size: 11px; font-weight: 600; letter-spacing: .22em; color: {GREEN}; text-transform: uppercase; }}
.mh-h1 {{ font-size: 26px; font-weight: 700; line-height: 1.15; margin: 6px 0 4px; letter-spacing: -.01em; color: {TXT}; }}
.mh-sub {{ font-size: 13px; color: {MUTED}; }}
.mh-chips {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }}
.mh-chip {{ font-size: 11.5px; font-weight: 600; color: {TXT}; border: 1px solid {LINE}; background: rgba(21,42,86,.75);
  border-radius: 999px; padding: 4px 11px; display: inline-flex; align-items: center; gap: 6px; }}
.mh-chip i {{ width: 7px; height: 7px; border-radius: 50%; background: {GREEN}; box-shadow: 0 0 0 3px rgba(45,214,140,.18);
  animation: mhblink 2.4s infinite; }}
.mh-chip.off i {{ background: {WARN}; box-shadow: 0 0 0 3px rgba(245,158,11,.18); }}
.mh-sky {{ flex: 1 1 auto; min-width: 280px; max-width: 640px; height: auto; margin: -14px -8px 0 auto; }}
.mh-kpis {{ position: relative; display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; margin-top: 10px; }}
.mh-k {{ background: rgba(21,42,86,.88); border: 1px solid {LINE}; border-radius: 12px; padding: 12px 14px 12px 16px;
  position: relative; overflow: hidden; height: 98px; box-sizing: border-box; display: flex; flex-direction: column; }}
.mh-k::before {{ content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: linear-gradient(180deg, {SKY}, {GREEN}); }}
.mh-k .l {{ font-size: 10.5px; font-weight: 600; letter-spacing: .14em; text-transform: uppercase; color: {MUTED};
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.mh-k .v {{ font-size: 24px; font-weight: 700; margin-top: 4px; letter-spacing: -.01em; color: {TXT}; line-height: 1.2;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.mh-k .v.g {{ background: linear-gradient(90deg, {SKY}, {GREEN}); -webkit-background-clip: text; background-clip: text; color: transparent; }}
.mh-k .s {{ font-size: 11.5px; color: {MUTED}; margin-top: auto; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.mh-route {{ animation: mhdash 3s linear infinite; }} .mh-lane {{ animation: mhdash 1.2s linear infinite; }}
.mh-truck {{ animation: mhdrive 14s linear infinite; }}
.mh-pulse {{ transform-box: fill-box; transform-origin: center; animation: mhpulse 2.4s ease-out infinite; }}
.mh-smoke {{ animation: mhsmoke 4s ease-in-out infinite; }} .mh-smoke.s2 {{ animation-delay: 1.5s; }}
@keyframes mhdash {{ to {{ stroke-dashoffset: -26; }} }}
@keyframes mhdrive {{ from {{ transform: translateX(30px); }} to {{ transform: translateX(640px); }} }}
@keyframes mhpulse {{ 0% {{ transform: scale(.6); opacity: .5; }} 100% {{ transform: scale(2.2); opacity: 0; }} }}
@keyframes mhsmoke {{ 0%, 100% {{ opacity: .35; transform: translateY(0); }} 50% {{ opacity: .9; transform: translateY(-3px); }} }}
@keyframes mhblink {{ 50% {{ opacity: .35; }} }}
@media (prefers-reduced-motion: reduce) {{ .mh * {{ animation: none !important; }} }}
@container (max-width: 1080px) {{ .mh-sky {{ display: none; }} }} @container (max-width: 760px) {{ .mh-kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} .mh-sep {{ display: none; }} .mh-top {{ flex-wrap: wrap; }} }}

/* sidebar brand */
.side-brand {{ display: flex; align-items: center; gap: 10px; margin: -.6rem 0 1.1rem; }}
.side-brand .ic {{ width: 42px; height: 42px; flex: none; }} .side-brand .ic svg {{ width: 100%; height: 100%; }}
.side-brand img {{ height: 38px; width: auto; }}

/* section titles, context rows, notices */
.sec {{ font-size: .95rem; font-weight: 700; color: {TXT}; margin: 0 0 .4rem; }}
.sec small {{ display: block; font-size: .78rem; font-weight: 500; color: {MUTED}; margin-top: .15rem; }}
.ctx-row {{ display: flex; gap: .75rem; align-items: flex-start; padding: .55rem 0; border-bottom: 1px solid {FAINT}; }}
.ctx-row:last-child {{ border-bottom: none; }}
.ctx-icon {{ width: 30px; height: 30px; border-radius: 8px; background: {BG}; border: 1px solid {LINE}; display: flex;
  align-items: center; justify-content: center; flex-shrink: 0; font-size: .9rem; color: {SKY}; }}
.ctx-main {{ color: {TXT}; font-weight: 600; font-size: .93rem; }}
.ctx-note {{ color: {MUTED}; font-size: .78rem; }}
.note {{ display: flex; gap: .8rem; align-items: flex-start; background: {CARD}; border: 1px solid {LINE};
  border-left: 4px solid {TEAL}; border-radius: 12px; padding: .75rem 1rem; margin: .4rem 0 .8rem; }}
.note.warn {{ border-color: rgba(245,158,11,.45); border-left-color: {WARN}; }}
.note .ni {{ font-weight: 700; color: {TEAL}; line-height: 1.4; }} .note.warn .ni {{ color: {WARN}; }}
.note .nt {{ color: {TXT}; font-weight: 600; font-size: .9rem; }}
.note .nb {{ color: {MUTED}; font-size: .83rem; margin-top: .1rem; }}

/* pipeline stages */
.pipe {{ display: flex; align-items: stretch; gap: 0; overflow-x: auto; padding: .3rem 2px .6rem; }}
.st-card {{ flex: 1 1 0; min-width: 118px; background: {CARD}; border: 1px solid {LINE}; border-radius: 14px;
  padding: .9rem .9rem .8rem; position: relative; }}
.st-card .n {{ font-size: .68rem; font-weight: 700; letter-spacing: .16em; color: {GREEN}; }}
.st-card .t {{ font-size: .95rem; font-weight: 700; color: {TXT}; margin: .25rem 0 .2rem; }}
.st-card .d {{ font-size: .76rem; color: {MUTED}; line-height: 1.35; }}
.st-card .m {{ margin-top: .55rem; font-size: 1.15rem; font-weight: 700; color: {SKY}; }}
.st-card .m span {{ font-size: .72rem; font-weight: 600; color: {MUTED}; margin-left: .25rem; }}
.st-card.last {{ border-color: {TEAL}; box-shadow: 0 0 0 1px rgba(30,198,207,.35) inset; }}
.st-arrow {{ flex: 0 0 22px; display: flex; align-items: center; justify-content: center; color: {TEAL}; }}
.src-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
.src {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 14px; padding: .9rem 1rem; }}
.src .t {{ color: {TXT}; font-weight: 700; font-size: .92rem; }}
.src .d {{ color: {MUTED}; font-size: .8rem; margin-top: .3rem; line-height: 1.45; }}
.src code {{ background: {BG}; color: {SKY}; padding: 1px 5px; border-radius: 5px; font-size: .75rem; }}
.foot {{ display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap; border-top: 1px solid {LINE};
  margin-top: 1.2rem; padding-top: .8rem; font-size: .78rem; color: {MUTED}; }}
.foot b {{ color: {TXT}; font-weight: 600; }}
@media (max-width: 900px) {{ .src-grid {{ grid-template-columns: 1fr; }} }}
/* KPI month-over-month delta */
.mh-k .srow {{ display: flex; align-items: center; gap: 7px; min-width: 0; }}
.mh-k .srow span {{ min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.dl {{ flex: none; font-size: 10.5px; font-weight: 700; padding: 1px 7px; border-radius: 999px; white-space: nowrap; }}
.dl.up {{ color: {GREEN}; background: rgba(45,214,140,.14); }}
.dl.down {{ color: {DOWN}; background: rgba(255,107,107,.14); }}
.dl.flat {{ color: {MUTED}; background: rgba(166,179,207,.12); }}

/* key findings */
.ins-head {{ display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; margin: .2rem 0 .55rem; }}
.ins-head .t {{ font-size: .78rem; font-weight: 700; letter-spacing: .18em; text-transform: uppercase; color: {GREEN}; }}
.ins-head .s {{ font-size: .78rem; color: {MUTED}; }}
.ins {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-bottom: 1rem; }}
.ins-c {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 14px; padding: 14px 16px; display: flex; gap: 14px;
  align-items: flex-start; position: relative; overflow: hidden; }}
.ins-c::after {{ content: ""; position: absolute; right: -30px; top: -30px; width: 90px; height: 90px; border-radius: 50%;
  background: radial-gradient(circle, rgba(30,198,207,.16), transparent 70%); }}
.ins-c .num {{ flex: none; min-width: 64px; font-size: 1.45rem; font-weight: 700; line-height: 1.1; color: {SKY}; }}
.ins-c.growth .num {{ color: {GREEN}; }} .ins-c.quality .num {{ color: {WARN}; }}
.ins-c .tag {{ font-size: .66rem; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; color: {MUTED}; }}
.ins-c .tt {{ font-size: .93rem; font-weight: 700; color: {TXT}; margin: .2rem 0 .25rem; line-height: 1.3; }}
.ins-c .bd {{ font-size: .8rem; color: {MUTED}; line-height: 1.45; }}

/* city profile */
.cp {{ background: linear-gradient(135deg, rgba(30,198,207,.10), rgba(45,214,140,.05) 60%, transparent), {CARD};
  border: 1px solid {LINE}; border-radius: 16px; padding: 16px 18px; margin-bottom: 1rem; }}
.cp-top {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; flex-wrap: wrap; }}
.cp .tag {{ font-size: .68rem; font-weight: 700; letter-spacing: .18em; text-transform: uppercase; color: {GREEN}; }}
.cp .nm {{ font-size: 1.3rem; font-weight: 700; color: {TXT}; margin-top: .15rem; }}
.cp .rg {{ font-size: .82rem; color: {MUTED}; }}
.cp-stats {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; margin: .9rem 0 .8rem; }}
.cp-s {{ background: rgba(10,20,48,.45); border: 1px solid {LINE}; border-radius: 10px; padding: 9px 11px; }}
.cp-s .l {{ font-size: .66rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: {MUTED}; }}
.cp-s .v {{ font-size: 1.12rem; font-weight: 700; color: {TXT}; margin-top: 2px; }}
.cp-s .v.up {{ color: {GREEN}; }} .cp-s .v.down {{ color: {DOWN}; }}
.cp-s .x {{ font-size: .72rem; color: {MUTED}; margin-top: 1px; }}
.cp-months {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }}
.cp-months .lbl {{ font-size: .75rem; color: {MUTED}; margin-right: 4px; }}
.mo {{ font-size: .75rem; font-weight: 700; padding: 4px 10px; border-radius: 8px; border: 1px solid {LINE}; position: relative; }}
.mo.ok {{ background: rgba(30,198,207,.16); color: {SKY}; border-color: rgba(30,198,207,.4); }}
.mo.miss {{ color: {MUTED}; border-style: dashed; opacity: .75; }}
.mo.flag::after {{ content: ""; position: absolute; top: -3px; right: -3px; width: 8px; height: 8px; border-radius: 50%;
  background: {WARN}; box-shadow: 0 0 0 2px {CARD}; }}
.cp-flags {{ font-size: .78rem; color: {MUTED}; margin-top: .6rem; }} .cp-flags b {{ color: {WARN}; }}
@container (max-width: 760px) {{ .cp-stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
@media (max-width: 1000px) {{ .ins {{ grid-template-columns: 1fr; }} .cp-stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
</style>
""")


# --------------------------------------------------------------------------- header
def _skyline() -> str:
    return f"""<svg class="mh-sky" viewBox="0 0 640 170" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
<defs><linearGradient id="skyg" x1="0" x2="640" y1="0" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{SKY}"/>
<stop offset=".55" stop-color="{TEAL}"/><stop offset="1" stop-color="{GREEN}"/></linearGradient>
<linearGradient id="skyfade" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".18" stop-color="#fff"/></linearGradient>
<mask id="skymask"><rect width="640" height="170" fill="url(#skyfade)"/></mask></defs>
<g mask="url(#skymask)">
<g fill="none" stroke="url(#skyg)" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round" opacity=".85">
<path d="M92 146 V92 M160 146 V92 M88 92 H164 M88 100 H164 M96 92 L104 100 M112 92 L120 100 M128 92 L136 100 M144 92 L152 100"/>
<path d="M108 100 v5 M144 100 v5"/><rect x="101" y="105" width="14" height="8" rx="2"/><rect x="137" y="105" width="14" height="8" rx="2"/>
<path d="M104 115 l-4 8 M148 115 l4 8" stroke-dasharray="2 3" opacity=".7"/>
<path d="M160 128 H190" stroke-width="2.4"/><circle cx="160" cy="128" r="2.5"/>
<path d="M182 140 V96 a11 11 0 0 1 22 0 V140 M208 140 V88 a11 11 0 0 1 22 0 V140 M182 110 H204 M208 106 H230"/>
<path d="M240 140 V104 L258 92 V104 L276 92 V104 L294 92 V140 M250 116 h8 M266 116 h8 M282 116 h8 M250 126 h8 M266 126 h8 M282 126 h8"/>
<path d="M302 140 L305 48 H315 L318 140 M304 70 H316 M303 96 H317"/>
<path class="mh-smoke" d="M310 42 c-6 -4 -2 -12 5 -10 c2 -7 12 -6 12 1 c6 -1 9 6 4 9"/>
<path d="M346 140 V44 M340 140 h12 M346 50 H416 M346 50 L362 44 L346 44 M352 56 L346 50 M400 50 V78 M394 78 h12 l-3 8 h-6 z
 M346 64 l8 -14 M346 80 l8 -16 M346 96 l8 -16 M346 112 l8 -16"/>
<path d="M430 140 L446 52 L462 140 M436 108 H456 M440 84 H452 M433 124 L459 108 M438 108 L454 84 M446 52 V44"/>
<path d="M474 140 V116 a16 6 0 0 1 32 0 V140 M474 116 a16 6 0 0 0 32 0 M512 140 V122 a12 5 0 0 1 24 0 V140"/>
<path d="M546 140 V108 L572 96 L598 108 V140 M558 140 V122 H586 V140 M606 140 L608 76 H616 L618 140"/>
<path class="mh-smoke s2" d="M612 70 c-5 -3 -2 -10 4 -8 c2 -6 10 -5 10 1"/>
</g>
<path d="M40 148 H640" stroke="{LINE}" stroke-width="10" stroke-linecap="round"/>
<path class="mh-lane" d="M40 148 H640" stroke="{MUTED}" stroke-width="1.4" stroke-dasharray="8 8" opacity=".6"/>
<g class="mh-truck"><rect x="0" y="137" width="22" height="9" rx="1.5" fill="{TEAL}"/><path d="M22 140 h6 l4 4 v2 h-10 z" fill="{SKY}"/>
<circle cx="6" cy="147" r="2.4" fill="{BG}" stroke="{SKY}" stroke-width="1.2"/><circle cx="26" cy="147" r="2.4" fill="{BG}" stroke="{SKY}" stroke-width="1.2"/></g>
<path class="mh-route" d="M120 34 C200 10 250 40 320 24 S 460 4 530 26" fill="none" stroke="url(#skyg)" stroke-width="2.2"
 stroke-dasharray="6 7" stroke-linecap="round"/>
<g fill="{BG}" stroke="{SKY}" stroke-width="2"><circle cx="120" cy="34" r="4"/><circle cx="214" cy="24" r="4"/>
<circle cx="320" cy="24" r="4"/><circle cx="430" cy="14" r="4"/></g>
<circle class="mh-pulse" cx="530" cy="22" r="10" fill="{GREEN}" opacity=".25"/>
<path d="M530 26 C524 19 521 15 521 11 a9 9 0 0 1 18 0 c0 4 -3 8 -9 15 z" fill="{GREEN}"/><circle cx="530" cy="11" r="3" fill="{BG}"/>
</g></svg>"""


def header(source_label: str, live: bool, updated: str, kpis: list[tuple],
           subtitle: str) -> str:
    """Brand header with the industrial skyline and five KPI cards.

    kpis: (label, value, sub, gradient_value[, (delta_text, "up"|"down"|"flat", tooltip)])
    """
    def card(l, v, s, g, delta=None):
        d = (f'<span class="dl {delta[1]}" title="{esc(delta[2] if len(delta) > 2 else "")}">{esc(delta[0])}</span>'
             if delta else "")
        return (f'<div class="mh-k"><div class="l" title="{esc(l)}">{esc(l)}</div>'
                f'<div class="v{" g" if g else ""}" title="{esc(v)}">{esc(v)}</div>'
                f'<div class="s srow">{d}<span title="{esc(s)}">{esc(s)}</span></div></div>')
    cards = "".join(card(*k) for k in kpis)
    wm = (f'<img class="wm" src="data:image/png;base64,{WORDMARK}" alt="MASAR مسار">' if WORDMARK
          else f'<div class="mh-h1" style="font-size:34px">MASAR</div>')
    return _flat(f"""<div class="mh"><div class="mh-top">
<div class="mh-brand"><div class="ic">{ICON_SVG}</div>{wm}</div><div class="mh-sep"></div>
<div class="mh-title"><div class="mh-eyebrow">Industrial Cities Data Hub</div>
<div class="mh-h1">Saudi Industrial Mobility Intelligence</div><div class="mh-sub">{esc(subtitle)}</div>
<div class="mh-chips"><span class="mh-chip{'' if live else ' off'}"><i></i>{esc(source_label)}</span>
<span class="mh-chip">Updated {esc(updated)}</span></div></div>
{_skyline()}</div><div class="mh-kpis">{cards}</div></div>""")


def side_brand() -> str:
    img = f'<img src="data:image/png;base64,{WORDMARK}" alt="MASAR مسار">' if WORDMARK else "<b>MASAR</b>"
    return _flat(f'<div class="side-brand"><div class="ic">{ICON_SVG}</div>{img}</div>')


# --------------------------------------------------------------------------- small pieces
def section(title: str, sub: str = "") -> str:
    return f'<div class="sec">{esc(title)}{f"<small>{esc(sub)}</small>" if sub else ""}</div>'


def ctx_row(icon: str, main: str, note: str) -> str:
    return (f'<div class="ctx-row"><div class="ctx-icon">{icon}</div><div>'
            f'<div class="ctx-main">{esc(main)}</div><div class="ctx-note">{esc(note)}</div></div></div>')


def note(title: str, body: str = "", kind: str = "info") -> str:
    """Dark notice card. kind = info (teal border) | warn (orange border). body may contain <b>."""
    icon = "!" if kind == "warn" else "i"
    return (f'<div class="note {kind}"><div class="ni">{icon}</div><div><div class="nt">{esc(title)}</div>'
            f'{f"<div class=nb>{body}</div>" if body else ""}</div></div>')


def pipeline(stages: list[tuple[str, str, str, str]]) -> str:
    """stages: (title, description, metric, metric_unit). Drawn as numbered cards joined by arrows."""
    arrow = ('<div class="st-arrow"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
             'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></div>')
    parts = []
    for i, (t, d, m, unit) in enumerate(stages, 1):
        last = " last" if i == len(stages) else ""
        metric = f'<div class="m">{esc(m)}<span>{esc(unit)}</span></div>' if m else ""
        parts.append(f'<div class="st-card{last}"><div class="n">STEP {i:02d}</div><div class="t">{esc(t)}</div>'
                     f'<div class="d">{esc(d)}</div>{metric}</div>')
    return '<div class="pipe">' + arrow.join(parts) + "</div>"


def sources(items: list[tuple[str, str]]) -> str:
    """items: (title, html description)."""
    return '<div class="src-grid">' + "".join(
        f'<div class="src"><div class="t">{esc(t)}</div><div class="d">{d}</div></div>' for t, d in items) + "</div>"


def footer(left: str, right: str) -> str:
    return f'<div class="foot"><span>{left}</span><span>{right}</span></div>'


def insights(items: list[dict], scope_note: str) -> str:
    cards = "".join(
        f'<div class="ins-c {esc(i["kind"])}"><div class="num">{esc(i["value"])}</div><div>'
        f'<div class="tag">{esc(i["tag"])}</div><div class="tt">{esc(i["title"])}</div>'
        f'<div class="bd">{esc(i["body"])}</div></div></div>' for i in items)
    return (f'<div class="ins-head"><span class="t">Key findings</span><span class="s">{esc(scope_note)}</span></div>'
            f'<div class="ins">{cards}</div>')


def city_profile(p: dict, fmt) -> str:
    """p from metrics.city_profile; fmt formats big numbers (e.g. 6.88M)."""
    g = p["growth"]
    if g:
        gv, gcls = f'{g["growth_pct"]:+.1f}%', "up" if g["growth_pct"] >= 0 else "down"
        gx = f'avg/month {fmt(g["q1_avg_monthly"])} → {fmt(g["q2_avg_monthly"])}'
    else:
        gv, gcls, gx = "Not compared", "", (p["growth_reason"] or "").lower() or "needs both quarters"
    peak = f'{p["peak"][0]:%b} · {fmt(p["peak"][1])}' if p["peak"] else "—"
    share = f'{p["region_share"]:.0%} of {p["region"]} region' if p["region_share"] is not None else ""
    stats = [("Movements", fmt(p["total"]), share, ""),
             ("Entries / exits", f'{fmt(p["entries"])} / {fmt(p["exits"])}',
              f'ratio {p["ratio"]:.2f}' if p["ratio"] is not None else "", ""),
             ("Growth Q1 → Q2", gv, gx, gcls),
             ("Peak month", peak, "highest monthly movement", ""),
             ("Months with data", f'{sum(m["has_data"] for m in p["months"])} / {len(p["months"])}',
              "missing months are never filled", "")]
    st_html = "".join(f'<div class="cp-s"><div class="l">{esc(l)}</div><div class="v {c}">{esc(v)}</div>'
                      f'<div class="x">{esc(x)}</div></div>' for l, v, x, c in stats)
    months = "".join(
        f'<span class="mo {"ok" if m["has_data"] else "miss"}{" flag" if m["flagged"] else ""}" '
        f'title="{"flagged" if m["flagged"] else ("data" if m["has_data"] else "no data")}">{m["month"]:%b}</span>'
        for m in p["months"])
    reasons = sorted(set(p["flag_reasons"]))
    flags = (f'<div class="cp-flags"><b>●</b> {len(p["flag_reasons"])} flagged month(s): {esc("; ".join(reasons))}</div>'
             if reasons else '<div class="cp-flags">No data-quality flags for this city.</div>')
    return _flat(f"""<div class="cp"><div class="cp-top"><div><div class="tag">City profile</div>
<div class="nm">{esc(p["name"])}</div><div class="rg">{esc(p["region"])} region</div></div></div>
<div class="cp-stats">{st_html}</div>
<div class="cp-months"><span class="lbl">Coverage Jan–Jun 2026</span>{months}</div>{flags}</div>""")


# --------------------------------------------------------------------------- charts
def style(fig: go.Figure, height: int = 360, title: str | None = None) -> go.Figure:
    """Quiet chart chrome on the navy surface."""
    fig.update_layout(
        height=height,
        title=dict(text=title, font=dict(size=15, color=TXT, family=FONT), x=0, xanchor="left") if title else None,
        margin=dict(l=4, r=12, t=44 if title else 12, b=4),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=MUTED, size=12),
        legend=dict(orientation="h", yanchor="top", y=-0.08, x=0, title=None,
                    font=dict(color=TXT), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=BG, bordercolor=LINE, font=dict(color=TXT, size=13, family=FONT)),
    )
    fig.update_xaxes(showgrid=False, title=None, linecolor=FAINT, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=FAINT, title=None, zeroline=False, tickfont=dict(color=MUTED))
    return fig