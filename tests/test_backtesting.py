import numpy as np
import pandas as pd
import pytest
from modules.backtesting import backtest_sales, summarize_backtesting, forecast_metrics, baseline_forecast
from modules.forecasting import prepare_weekly

def test_forecast_metrics_perfect_predictions():
    actual = np.array([100, 200, 300])
    result = forecast_metrics(actual, actual)
    assert result["MAE"] == 0
    assert result["RMSE"] == 0
    assert result["WAPE"] == 0

def test_last_week_baseline(sample_walmart):
    weekly = prepare_weekly(sample_walmart)
    result = baseline_forecast(weekly["Sales"].iloc[:90], 4, "Last Week")
    assert len(result) == 4
    assert result["PredictedSales"].nunique() == 1

def test_seasonal_baseline(sample_walmart):
    weekly = prepare_weekly(sample_walmart)
    history = weekly["Sales"].iloc[:90]
    result = baseline_forecast(history, 4, "Seasonal Naive")
    assert len(result) == 4
    assert np.isclose(result["PredictedSales"].iloc[0], history.iloc[-52])

def test_backtesting_produces_three_models(sample_walmart):
    results, predictions = backtest_sales(sample_walmart, n_splits=2, test_weeks=8, min_train_weeks=70)
    assert len(results) == 6
    assert set(results["Model"]) == {"Random Forest", "Last Week", "Seasonal Naive"}
    assert len(predictions) == 48
    assert results["MAE"].notna().all()

def test_backtesting_chronology(sample_walmart):
    results, predictions = backtest_sales(sample_walmart, n_splits=2, test_weeks=8, min_train_weeks=70)
    first_fold = results[results["Fold"] == 1].iloc[0]
    second_fold = results[results["Fold"] == 2].iloc[0]
    assert first_fold["TestEnd"] < second_fold["TestStart"]
    assert first_fold["TrainWeeks"] < second_fold["TrainWeeks"]

def test_backtesting_summary(sample_walmart):
    results, predictions = backtest_sales(sample_walmart, n_splits=2, test_weeks=8, min_train_weeks=70)
    summary = summarize_backtesting(results, predictions)
    assert len(summary) == 3
    assert summary["WAPE"].is_monotonic_increasing

def test_insufficient_history(sample_walmart):
    short = sample_walmart[sample_walmart["Date"] < sample_walmart["Date"].min() + pd.Timedelta(weeks=40)]
    with pytest.raises(ValueError):
        backtest_sales(short, n_splits=3, test_weeks=8, min_train_weeks=70)