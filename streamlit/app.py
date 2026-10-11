"""Masar — Saudi Industrial Mobility Intelligence dashboard (SDA-21).

Answers the Operations Manager's questions:
  1. Which industrial cities and regions are busiest, and which grew fastest Q1 → Q2?
  2. How does movement change month by month?
  3. What was the weather and event context? (context, not cause)

Run:   streamlit run app.py   (from inside the streamlit folder)
Data:  see data_source.py  (MASAR_DATA_SOURCE = auto | bigquery | local | snapshot)
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data_source
import metrics
import theme as T

st.set_page_config(page_title="Masar · Industrial Mobility", page_icon="🧭", layout="wide")
st.markdown(T.CSS, unsafe_allow_html=True)


def num(n) -> str:
    if n is None or pd.isna(n):
        return "—"
    n = float(n)
    if abs(n) >= 1e6:
        return f"{n / 1e6:.2f}M"
    if abs(n) >= 1e3:
        return f"{n / 1e3:.0f}K"
    return f"{n:,.0f}"


def table(df: pd.DataFrame) -> pd.DataFrame:
    """Readable copy for st.dataframe: months as 'Jan 2026'."""
    out = df.copy()
    if "month_start" in out:
        out["month_start"] = pd.to_datetime(out["month_start"]).dt.strftime("%b %Y")
    return out


def label_positions(values: dict, min_gap: float) -> dict:
    """Spread end-of-line labels so close values don't overlap (returns y per label)."""
    placed, last = {}, None
    for name, y in sorted(values.items(), key=lambda kv: kv[1]):
        y = y if last is None or y - last >= min_gap else last + min_gap
        placed[name], last = y, y
    return placed


def show(fig, height, title=None):
    st.plotly_chart(T.style(fig, height, title), use_container_width=True,
                    config={"displayModeBar": False})


# --------------------------------------------------------------------------- data
@st.cache_data(ttl=600, show_spinner="Loading pipeline data…")
def get_data():
    return data_source.load()


result = get_data()

st.markdown('<div class="masar-eyebrow">SDA × Le Wagon · Data Engineering</div>'
            '<div class="masar-title">مسار · Saudi Industrial Mobility Intelligence</div>'
            '<div class="masar-sub">Vehicle entries and exits across Saudi industrial cities, '
            'January–June 2026, with weather and government-event context.</div>',
            unsafe_allow_html=True)

if result.data is None:
    st.error(f"**Data is not available right now.** {result.error}")
    st.markdown("- **BigQuery:** check your Google credentials and that dbt built "
                f"`{data_source.MART_TABLE}`.\n"
                "- **Local:** run `python -m ingestion.run` from the repo root, "
                "then set `MASAR_DATA_SOURCE=local`.")
    st.stop()

data = result.data.copy()
data["month_start"] = pd.to_datetime(data["month_start"])

pills = T.pill("Source", result.label) + T.pill("Data last updated", result.updated or "unknown")
pills += T.pill("Values", "real pipeline data — no mock-up numbers")
st.markdown(pills, unsafe_allow_html=True)
if result.notes:
    with st.expander("Data source details"):
        if result.source != "bigquery":
            st.markdown("BigQuery is not connected on this computer, so the page uses the "
                        "next available source. Connect Google credentials to read the live mart.")
        for note in result.notes:
            st.caption(note)

# --------------------------------------------------------------------------- filters
with st.sidebar:
    st.markdown("### Filters")
    regs = data[["region_code", "region_name"]].drop_duplicates().sort_values("region_name")
    reg_names = dict(zip(regs.region_code, regs.region_name))
    sel_regions = st.multiselect("Region", list(reg_names), format_func=reg_names.get,
                                 placeholder="All regions")
    pool = data if not sel_regions else data[data.region_code.isin(sel_regions)]
    cts = pool[["city_code", "city_name"]].drop_duplicates().sort_values("city_name")
    city_names = dict(zip(cts.city_code, cts.city_name))
    sel_cities = st.multiselect("Industrial city", list(city_names), format_func=city_names.get,
                                placeholder="All cities")
    months = sorted(data.month_start.unique())
    sel_months = st.multiselect("Month", months, format_func=lambda m: pd.Timestamp(m).strftime("%b %Y"),
                                placeholder="All months")
    st.caption("Empty = all. Traffic data is monthly, so there is no day-level filter.")
    st.divider()
    st.caption("Weather and events are shown as **context only** — six months of data "
               "cannot prove they cause changes in movement.")

view = metrics.filter_data(data, sel_regions, sel_cities, sel_months)
view_all_months = metrics.filter_data(data, sel_regions, sel_cities, None)
if view.empty:
    st.warning("No data for this combination of filters. Try removing a filter.")
    st.stop()

avail = metrics.context_available(view)
k = metrics.kpis(view)

# --------------------------------------------------------------------------- KPI cards
c = st.columns(5)
c[0].markdown(T.kpi("Total vehicle movements", num(k["total"]),
                    f"{num(k['entries'])} entries · {num(k['exits'])} exits"), unsafe_allow_html=True)
c[1].markdown(T.kpi("Busiest industrial city", k["busiest_city"] or "—",
                    f"{k['busiest_city_share']:.0%} of movements in scope" if k["busiest_city_share"] else ""),
              unsafe_allow_html=True)
c[2].markdown(T.kpi("Busiest region", k["busiest_region"] or "—",
                    f"{k['busiest_region_share']:.0%} of movements in scope" if k["busiest_region_share"] else ""),
              unsafe_allow_html=True)
c[3].markdown(T.kpi("Entry / exit ratio", "—" if k["ratio"] is None else f"{k['ratio']:.2f}",
                    "Balanced flow ≈ 1.00 · quality indicator"), unsafe_allow_html=True)
if avail["weather"]:
    c[4].markdown(T.kpi("Average temperature", f"{view.avg_temp_c.mean():.1f} °C",
                        "Open-Meteo · context only"), unsafe_allow_html=True)
else:
    c[4].markdown(T.kpi("Industrial cities in scope", str(k["cities"]),
                        "Weather: pending"), unsafe_allow_html=True)

st.write("")

# --------------------------------------------------------------------------- map + trend
left, right = st.columns([3, 2])
with left:
    with st.container(border=True):
        pts = metrics.map_points(view)
        pts["total_movements"] = pts["total_movements"].astype(float)
        fig = px.scatter_geo(
            pts, lat="latitude", lon="longitude", size="total_movements", color="region_name",
            color_discrete_map=T.REGION_COLORS, hover_name="city_name", size_max=34,
            hover_data={"total_movements": ":,.0f", "region_name": True,
                        "latitude": False, "longitude": False},
        )
        fig.update_traces(marker=dict(line=dict(width=1, color=T.BG), opacity=0.9))
        fig.update_geos(  # drawn locally: no map tiles, no API key needed
            projection_type="mercator", lataxis_range=[15.5, 32.5], lonaxis_range=[34, 56],
            showland=True, landcolor=T.LAND, showocean=True, oceancolor=T.SEA,
            showlakes=False, showcountries=True, countrycolor=T.BORDER, showcoastlines=True,
            coastlinecolor=T.BORDER, showframe=False, bgcolor="rgba(0,0,0,0)", resolution=50,
        )
        show(fig, 400, "Industrial network pulse — marker size = vehicle movements")
with right:
    with st.container(border=True):
        trend = metrics.monthly_trend(view, "region")
        fig = px.line(trend, x="month_start", y="total_movements", color="region_name",
                      color_discrete_map=T.REGION_COLORS, markers=True)
        fig.update_traces(line_width=2, marker_size=8,
                          hovertemplate="%{fullData.name}: %{y:,.0f}<extra></extra>")
        fig.update_layout(hovermode="x unified", showlegend=False)
        fig.update_xaxes(dtick="M1", tickformat="%b")
        ends = {n: g.iloc[-1] for n, g in trend.groupby("region_name")}
        ys = label_positions({n: float(r.total_movements) for n, r in ends.items()},
                             min_gap=0.06 * float(trend.total_movements.max()))
        for name, r in ends.items():  # direct labels: colour is never the only cue
            fig.add_annotation(x=r.month_start, y=ys[name], text=name, showarrow=False,
                               xanchor="left", xshift=8, font=dict(color=T.CREAM, size=11))
        show(fig, 400, "Monthly movement trend by region")
        st.caption("Gaps = no data reported for that month (see Data quality).")

# --------------------------------------------------------------------------- comparison + context
left, right = st.columns([3, 2])
with left:
    with st.container(border=True):
        by_city = metrics.totals_by(view, "city").sort_values("total_movements")
        fig = go.Figure(go.Bar(
            x=by_city.total_movements.astype(float), y=by_city.city_name, orientation="h",
            marker=dict(color=T.ACCENT, cornerradius=4),
            text=[num(v) for v in by_city.total_movements], textposition="outside", cliponaxis=False,
            customdata=np.stack([by_city.region_name, by_city.entries.astype(float),
                                 by_city.exits.astype(float)], axis=-1),
            hovertemplate="<b>%{y}</b> · %{customdata[0]}<br>Total: %{x:,.0f}<br>"
                          "Entries: %{customdata[1]:,.0f} · Exits: %{customdata[2]:,.0f}<extra></extra>",
        ))
        fig.update_xaxes(showticklabels=False, showgrid=False,
                         range=[0, float(by_city.total_movements.max()) * 1.18])
        show(fig, 70 + 32 * len(by_city), "Industrial city comparison — total movements")

with right:
    with st.container(border=True):
        st.markdown("##### Weather context")
        if avail["weather"]:
            ctx = metrics.monthly_context(view)
            hottest = ctx.loc[ctx.avg_temp_c.idxmax()]
            st.markdown(
                T.ctx_row("☀", f"{view.avg_temp_c.mean():.1f} °C average", "Across selected cities and months")
                + T.ctx_row("↗", f"{hottest.month_start:%B} is the hottest month",
                            f"{hottest.avg_temp_c:.1f} °C average")
                + T.ctx_row("🔥", f"{int(view.hot_days.fillna(0).sum())} hot city-days",
                            f"Days with max ≥ {metrics.HOT_DAY_C:.0f} °C"),
                unsafe_allow_html=True)
        else:
            st.markdown(T.ctx_row("…", "Pending", "Weather appears once weather_daily is loaded"),
                        unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("##### Government events")
        if avail["events"]:
            ev = view.groupby("month_start", as_index=False)["event_count"].sum()
            top = ev.loc[ev.event_count.idxmax()]
            busiest_ev = view.groupby("city_name")["event_count"].sum().idxmax()
            st.markdown(
                T.ctx_row("●", f"{top.month_start:%B} has the most events",
                          f"{int(top.event_count)} event links to selected cities")
                + T.ctx_row("◆", f"{busiest_ev}", "Industrial city with the most linked events")
                + T.ctx_row("i", "Linked by the city rule",
                            "Same city → that industrial city; same region → all cities in the region"),
                unsafe_allow_html=True)
        else:
            st.markdown(T.ctx_row("…", "Pending", "Events appear once event_days is loaded"),
                        unsafe_allow_html=True)
        st.markdown('<div class="masar-note">Context only — not a proven cause of movement changes.</div>',
                    unsafe_allow_html=True)

st.write("")

# --------------------------------------------------------------------------- detail tabs
t_growth, t_region, t_quality, t_context, t_table, t_pipe = st.tabs(
    ["Growth Q1 → Q2", "Regions & entries vs exits", "Data quality", "Weather & events by month",
     "Data table", "Pipeline"])

with t_growth:
    st.markdown("**Which cities grew fastest from Q1 to Q2 2026?**")
    st.caption("Compares the **average monthly movement** per quarter, because some cities miss months. "
               "Only cities with data in both quarters are compared.")
    growth, excluded = metrics.growth_q1_q2(view_all_months)
    if growth.empty:
        st.info("None of the selected cities has data in both quarters.")
    else:
        g = growth.sort_values("growth_pct")
        fig = go.Figure(go.Bar(
            x=g.growth_pct, y=g.city_name, orientation="h",
            marker=dict(color=[T.UP if v >= 0 else T.DOWN for v in g.growth_pct], cornerradius=4),
            text=[f"{v:+.1f}%" for v in g.growth_pct], textposition="outside", cliponaxis=False,
            customdata=np.stack([g.q1_avg_monthly, g.q2_avg_monthly, g.q1_months, g.q2_months], axis=-1),
            hovertemplate=("<b>%{y}</b><br>Growth: %{x:+.1f}%<br>"
                           "Q1 avg/month: %{customdata[0]:,.0f} (%{customdata[2]} months)<br>"
                           "Q2 avg/month: %{customdata[1]:,.0f} (%{customdata[3]} months)<extra></extra>"),
        ))
        fig.add_vline(x=0, line_color=T.MUTED, line_width=1)
        show(fig, 70 + 36 * len(g), "Change in average monthly movement, Q1 → Q2")
        short = growth[(growth.q1_months < 3) | (growth.q2_months < 3)]
        if not short.empty:
            st.warning("Based on fewer than 3 months in a quarter: " + ", ".join(short.city_name)
                       + ". Read with care.")
    if not excluded.empty:
        st.caption("Not compared (one quarter only): "
                   + ", ".join(f"{r.city_name} ({r.reason.lower()})" for r in excluded.itertuples()))

with t_region:
    a, b = st.columns(2)
    with a:
        by_region = metrics.totals_by(view, "region").sort_values("total_movements")
        fig = go.Figure(go.Bar(
            x=by_region.total_movements.astype(float), y=by_region.region_name, orientation="h",
            marker=dict(color=[T.REGION_COLORS.get(r, T.ACCENT) for r in by_region.region_name],
                        cornerradius=4),
            text=[num(v) for v in by_region.total_movements], textposition="outside", cliponaxis=False,
            hovertemplate="%{y}: %{x:,.0f}<extra></extra>"))
        fig.update_xaxes(showticklabels=False, showgrid=False,
                         range=[0, float(by_region.total_movements.max()) * 1.2])
        show(fig, 300, "Total movements by region")
    with b:
        city = st.selectbox("City", sorted(view.city_name.unique()), key="ee_city")
        one = view[view.city_name == city].sort_values("month_start")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=one.month_start, y=one.entries.astype(float), name="Entries",
                                 mode="lines+markers", line=dict(color=T.ENTRIES, width=2), marker_size=8))
        fig.add_trace(go.Scatter(x=one.month_start, y=one.exits.astype(float), name="Exits",
                                 mode="lines+markers", line=dict(color=T.EXITS, width=2), marker_size=8))
        fig.update_traces(hovertemplate="%{fullData.name}: %{y:,.0f}<extra></extra>")
        fig.update_layout(hovermode="x unified")
        fig.update_xaxes(dtick="M1", tickformat="%b")
        show(fig, 300, f"{city} — entries vs exits")

with t_quality:
    st.caption(f"The entry/exit ratio is a **data-quality indicator first**. A city-month is flagged when "
               f"entries and exits differ by more than {metrics.IMBALANCE_LIMIT:.0%} (ratio below "
               f"{metrics.RATIO_LOW:.2f} or above {metrics.RATIO_HIGH:.2f}) — the same rule as the "
               f"ingestion quality flag — or when the pipeline flags repeated values.")
    heat = view.pivot_table(index="city_name", columns="month_start", values="entry_exit_ratio")
    heat.columns = [pd.Timestamp(c).strftime("%b") for c in heat.columns]
    fig = go.Figure(go.Heatmap(
        z=np.log2(heat.astype(float)).values, x=list(heat.columns), y=list(heat.index),
        text=[["" if pd.isna(v) else f"{v:.2f}" for v in row] for row in heat.values],
        texttemplate="%{text}", customdata=heat.values,
        colorscale=[[0, T.DOWN], [0.5, T.NEUTRAL_MID], [1, T.UP]], zmid=0, zmin=-1.5, zmax=1.5,
        xgap=2, ygap=2,
        hovertemplate="%{y} · %{x}<br>Entry/exit ratio: %{customdata:.2f}<extra></extra>",
        colorbar=dict(title="ratio", tickvals=[-1, 0, 1], ticktext=["0.5", "1.0", "2.0"],
                      tickfont=dict(color=T.MUTED))))
    show(fig, 80 + 30 * len(heat), "Entry / exit ratio by city and month (blank = no data)")
    flags = metrics.quality_flags(view)
    st.markdown(f"**⚠ Flagged city-months: {len(flags)}**")
    if not flags.empty:
        st.dataframe(table(flags), use_container_width=True, hide_index=True)
    gaps = metrics.missing_months(view_all_months)
    st.markdown(f"**Cities with missing months: {len(gaps)}** — never filled in, shown as gaps")
    if not gaps.empty:
        st.dataframe(gaps, use_container_width=True, hide_index=True)

with t_context:
    st.warning("Context only: with six months of data, weather and events cannot be shown to "
               "**cause** changes in vehicle movement.")
    ctx = metrics.monthly_context(view)
    fig = go.Figure(go.Bar(x=ctx.month_start, y=ctx.total_movements.astype(float),
                           marker=dict(color=T.ACCENT, cornerradius=4),
                           hovertemplate="%{x|%b}: %{y:,.0f}<extra></extra>"))
    fig.update_xaxes(dtick="M1", tickformat="%b")
    show(fig, 260, "Vehicle movements per month")
    a, b = st.columns(2)
    with a:
        if avail["weather"]:
            fig = go.Figure(go.Scatter(x=ctx.month_start, y=ctx.avg_temp_c, mode="lines+markers",
                                       line=dict(color=T.EXITS, width=2), marker_size=8,
                                       hovertemplate="%{x|%b}: %{y:.1f} °C<extra></extra>"))
            fig.update_xaxes(dtick="M1", tickformat="%b")
            show(fig, 240, "Average temperature (°C)")
        else:
            st.info("**Weather: pending** — appears once weather_daily is loaded.")
    with b:
        if avail["events"]:
            fig = go.Figure(go.Bar(x=ctx.month_start, y=ctx.event_count.astype(float),
                                   marker=dict(color="#199e70", cornerradius=4),
                                   hovertemplate="%{x|%b}: %{y:,.0f} event links<extra></extra>"))
            fig.update_xaxes(dtick="M1", tickformat="%b")
            show(fig, 240, "Government event links per month")
        else:
            st.info("**Events: pending** — appear once event_days is loaded.")

with t_table:
    st.caption("Every number on this page comes from this table (one row per industrial city per month).")
    st.dataframe(table(view.drop(columns=["latitude", "longitude"])), use_container_width=True, hide_index=True)
    st.download_button("Download CSV", table(view).to_csv(index=False).encode("utf-8"),
                       "masar_city_month.csv", "text/csv")

with t_pipe:
    # Kept from the first version: source files found by Airflow.
    project_dir = Path(os.environ.get("MASAR_PROJECT_DIR", Path(__file__).resolve().parent.parent))
    inventory_file = project_dir / "data" / "processed" / "workbook_inventory.csv"
    source_files = sorted(project_dir.glob("*.xlsx"))
    a, b = st.columns(2)
    a.metric("Excel source files", len(source_files))
    if inventory_file.exists():
        inventory = pd.read_csv(inventory_file)
        b.metric("Worksheets", len(inventory))
        st.dataframe(inventory, use_container_width=True, hide_index=True)
    else:
        b.metric("Worksheets", "—")
        if source_files:
            st.dataframe(pd.DataFrame({"file_name": [p.name for p in source_files]}),
                         use_container_width=True, hide_index=True)
    st.caption("Pipeline: Excel + Open-Meteo → Python ingestion → Cloud Storage → BigQuery (masar_raw) "
               "→ dbt → Streamlit. Orchestrated by Airflow.")

st.divider()
st.caption("Masar · SDA × Le Wagon Data Engineering · Traffic: quarterly industrial-city files (gate cameras) · "
           "Weather: Open-Meteo · Events: public-sector event approvals")