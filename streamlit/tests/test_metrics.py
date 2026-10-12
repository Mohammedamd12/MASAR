"""Dashboard numbers. Run from the streamlit folder:  pytest tests -q"""
from pathlib import Path

import pandas as pd
import pytest

import metrics

SNAP = Path(__file__).resolve().parents[1] / "snapshot"


@pytest.fixture
def seeds():
    return pd.read_csv(SNAP / "industrial_cities.csv"), pd.read_csv(SNAP / "regions.csv")


@pytest.fixture
def data():
    return pd.read_csv(SNAP / "city_month_snapshot.csv", parse_dates=["month_start"])


def test_one_row_per_city_month(data):
    assert not data.duplicated(["city_code", "month_start"]).any()


def test_totals_reconcile_with_excel_files(data):
    # Sum of every vehicle count in Traffic (3).xlsx + Traffic (4).xlsx
    assert int(data.total_movements.sum()) == 20_707_074


def test_every_city_has_region_and_coordinates(data):
    assert data[["region_name", "latitude", "longitude"]].notna().all().all()


def test_builds_from_dbt_mart_shape(seeds):
    mart = pd.DataFrame({"city_name": ["Riyadh 2nd Industrial City "], "movement_month": ["2026-01-01"],
                         "total_entries": [10], "total_exits": [8], "total_movement": [18]})
    out = metrics.build_city_month(mart, *seeds)
    assert out.loc[0, "city_code"] == "RUH2"
    assert out.loc[0, "region_name"] == "Riyadh"
    assert out.loc[0, "total_movements"] == 18


def test_weather_and_events_aggregate_monthly(seeds):
    traffic = pd.DataFrame({"city_code": ["TAB"], "month_start": ["2026-06-01"], "entries": [5], "exits": [5]})
    weather = pd.DataFrame({"city_code": ["TAB"] * 3,
                            "weather_date": ["2026-06-01", "2026-06-02", "2026-06-03"],
                            "temperature_2m_mean": [30, 32, 34], "temperature_2m_max": [39, 41, 42],
                            "precipitation_sum": [0, 1, 0]})
    events = pd.DataFrame({"gov_request_number": ["A", "A", "B"], "city_code": ["TAB"] * 3,
                           "event_date": ["2026-06-01", "2026-06-02", "2026-06-10"]})
    out = metrics.build_city_month(traffic, *seeds, weather, events).iloc[0]
    assert out.avg_temp_c == 32.0
    assert out.hot_days == 2
    assert out.event_count == 2  # a 2-day event counts once


def test_growth_uses_monthly_average_not_totals():
    df = pd.DataFrame({"city_code": ["a"] * 4, "city_name": ["A"] * 4,
                       "quarter": ["2026-Q1"] * 3 + ["2026-Q2"],
                       "month_start": pd.to_datetime(["2026-01-01", "2026-02-01", "2026-03-01", "2026-06-01"]),
                       "total_movements": [100, 100, 100, 100]})
    growth, excluded = metrics.growth_q1_q2(df)
    assert growth.iloc[0].growth_pct == 0.0  # totals would wrongly show -67%
    assert excluded.empty


def test_growth_excludes_single_quarter_cities(data):
    growth, excluded = metrics.growth_q1_q2(data)
    assert set(excluded.city_code) == {"KHJ", "ZLF", "RUH3", "HFR", "QAS"}
    assert len(growth) == 7


def test_missing_months(data):
    gaps = metrics.missing_months(data).set_index("city_code")
    assert gaps.loc["TAB", "missing_months"] == "Apr"
    assert gaps.loc["SDR", "missing_months"] == "Apr, May"


def test_quality_flags_match_pipeline(data):
    flags = metrics.quality_flags(data)
    assert "Dammam 2nd Industrial City" in set(flags.city_name)
    sudair = flags[flags.city_name.str.startswith("Sudair")]
    assert sudair.reason.str.contains("repeated").any()


def test_kpis_follow_filters(data):
    k = metrics.kpis(metrics.filter_data(data, regions=["MAK"]))
    assert k["busiest_region"] == "Makkah" and k["cities"] == 1


def test_empty_filter_means_all(data):
    assert len(metrics.filter_data(data, [], [], [])) == len(data)


def test_month_change_is_like_for_like(data):
    mc = metrics.month_change(data, "2026-06-01")
    # Sudair has no May and three cities appear only in June: they are left out of the comparison
    assert mc["prev"] == pd.Timestamp("2026-05-01")
    assert mc["cities"] < mc["cities_now"]
    may = data[data.month_start == "2026-05-01"]
    jun = data[(data.month_start == "2026-06-01") & data.city_code.isin(may.city_code)]
    expected = (jun.total_movements.sum() - may.total_movements.sum()) / may.total_movements.sum() * 100
    assert mc["total_pct"] == pytest.approx(expected)


def test_month_change_has_no_previous_for_january(data):
    assert metrics.month_change(data, "2026-01-01") is None


def test_insights_volume_growth_quality(data):
    items = metrics.insights(data, data)
    assert [i["kind"] for i in items] == ["volume", "growth", "quality"]
    assert "Dammam 2nd" in items[0]["title"]
    assert items[1]["value"] == "+25.3%" and "Madn Oasis Jeddah" in items[1]["title"]
    assert items[2]["value"] == "4/6"


def test_city_profile_single_quarter_city_is_not_compared(data):
    p = metrics.city_profile(data, data, "ZLF")
    assert p["growth"] is None and p["growth_reason"] == "Only in Q1"
    assert sum(m["has_data"] for m in p["months"]) == 3