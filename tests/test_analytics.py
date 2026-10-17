import numpy as np
import pandas as pd
from modules.analytics import calculate_kpis, weekly_sales, store_performance
from modules.performance_intelligence import weekly_comparison, performance_alerts

def test_sales_total_matches_source(sample_walmart):
    kpis = calculate_kpis(sample_walmart)
    assert np.isclose(kpis["Total Sales"], sample_walmart["Weekly_Sales"].sum())

def test_store_and_department_counts(sample_walmart):
    kpis = calculate_kpis(sample_walmart)
    assert kpis["Stores"] == 2
    assert kpis["Departments"] == 2

def test_weekly_aggregation(sample_walmart):
    result = weekly_sales(sample_walmart)
    assert len(result) == 110
    assert np.isclose(result["Weekly_Sales"].sum(), sample_walmart["Weekly_Sales"].sum())

def test_store_totals_reconcile(sample_walmart):
    result = store_performance(sample_walmart)
    assert np.isclose(result["TotalSales"].sum(), sample_walmart["Weekly_Sales"].sum())

def test_week_over_week_calculation(sample_walmart):
    result = weekly_comparison(sample_walmart)
    assert result["CurrentSales"] is not None
    assert np.isfinite(result["WoW"])

def test_store_decline_alert(sample_walmart):
    dates = sorted(sample_walmart["Date"].unique())
    data = sample_walmart.copy()
    data.loc[(data["Store"] == 1) & (data["Date"] == dates[-1]), "Weekly_Sales"] *= 0.50
    alerts = performance_alerts(data, threshold=-10)
    flagged = alerts[alerts["Status"] == "Attention"]
    assert 1 in flagged["Store"].tolist()