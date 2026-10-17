import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from modules.forecasting import FEATURES, create_features, prepare_weekly, recursive_forecast

def forecast_metrics(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    mae = mean_absolute_error(actual, predicted)
    rmse = np.sqrt(mean_squared_error(actual, predicted))
    denominator = np.abs(actual).sum()
    wape = np.abs(actual - predicted).sum() / denominator * 100 if denominator > 0 else np.nan
    return {"MAE": mae, "RMSE": rmse, "WAPE": wape}

def baseline_forecast(history, horizon, method):
    values = history.copy()
    predictions = []
    for step in range(horizon):
        date = values.index[-1] + pd.Timedelta(weeks=1)
        if method == "Last Week":
            prediction = float(values.iloc[-1])
        elif method == "Seasonal Naive":
            prediction = float(values.iloc[-52]) if len(values) >= 52 else float(values.iloc[-1])
        else:
            raise ValueError(f"Unknown baseline: {method}")
        predictions.append({"Date": date, "PredictedSales": prediction})
        values.loc[date] = prediction
    return pd.DataFrame(predictions)

def backtest_sales(df, n_splits=3, test_weeks=8, min_train_weeks=70):
    weekly = prepare_weekly(df)
    required = min_train_weeks + n_splits * test_weeks
    if len(weekly) < required:
        raise ValueError(f"At least {required} continuous weeks are required. Available: {len(weekly)}.")
    if min_train_weeks < 60:
        raise ValueError("Use at least 60 training weeks for the 52-week seasonal lag.")
    if n_splits < 1 or test_weeks < 1:
        raise ValueError("Splits and test weeks must be positive.")

    results = []
    predictions = []
    first_test = len(weekly) - n_splits * test_weeks

    for fold in range(n_splits):
        test_start = first_test + fold * test_weeks
        test_end = test_start + test_weeks
        train = weekly.iloc[:test_start].copy()
        test = weekly.iloc[test_start:test_end].copy()
        features = create_features(train)
        if features.empty:
            raise ValueError(f"No training features for fold {fold + 1}.")

        model = RandomForestRegressor(n_estimators=120, max_depth=8, min_samples_leaf=2, random_state=42, n_jobs=-1)
        model.fit(features[FEATURES], features["Sales"])

        outputs = {
            "Random Forest": recursive_forecast(model, train["Sales"], test_weeks),
            "Last Week": baseline_forecast(train["Sales"], test_weeks, "Last Week"),
            "Seasonal Naive": baseline_forecast(train["Sales"], test_weeks, "Seasonal Naive")
        }

        for name, output in outputs.items():
            actual = test["Sales"].to_numpy()
            predicted = output["PredictedSales"].to_numpy()
            scores = forecast_metrics(actual, predicted)
            results.append({"Fold": fold + 1, "Model": name, "TrainWeeks": len(train), "TestWeeks": len(test), "TestStart": test.index.min(), "TestEnd": test.index.max(), **scores})
            for date, actual_value, predicted_value in zip(test.index, actual, predicted):
                predictions.append({"Fold": fold + 1, "Date": date, "Model": name, "ActualSales": float(actual_value), "PredictedSales": float(predicted_value)})

    return pd.DataFrame(results), pd.DataFrame(predictions)

def summarize_backtesting(results, predictions=None):
    if results.empty:
        return pd.DataFrame(columns=["Model", "MAE", "RMSE", "WAPE", "Folds"])
    if predictions is not None and not predictions.empty:
        rows = []
        for model, group in predictions.groupby("Model"):
            metrics = forecast_metrics(group["ActualSales"], group["PredictedSales"])
            rows.append({"Model": model, **metrics, "Folds": group["Fold"].nunique()})
        return pd.DataFrame(rows).sort_values("WAPE").reset_index(drop=True)
    summary = results.groupby("Model", as_index=False).agg(MAE=("MAE", "mean"), RMSE=("RMSE", "mean"), WAPE=("WAPE", "mean"), Folds=("Fold", "nunique"))
    return summary.sort_values("WAPE").reset_index(drop=True)