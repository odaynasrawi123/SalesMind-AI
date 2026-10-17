import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

LAGS = [1, 2, 4, 8, 52]
FEATURES = [f"lag_{lag}" for lag in LAGS] + ["rolling_4", "rolling_8", "week_sin", "week_cos", "trend"]

def create_features(weekly):
    data = weekly.copy()
    for lag in LAGS:
        data[f"lag_{lag}"] = data["Sales"].shift(lag)
    data["rolling_4"] = data["Sales"].shift(1).rolling(4).mean()
    data["rolling_8"] = data["Sales"].shift(1).rolling(8).mean()
    week = data.index.isocalendar().week.astype(int)
    data["week_sin"] = np.sin(2 * np.pi * week / 52.18)
    data["week_cos"] = np.cos(2 * np.pi * week / 52.18)
    data["trend"] = np.arange(len(data))
    return data.dropna(subset=FEATURES)

def prepare_weekly(df):
    weekly = df.groupby("Date")["Weekly_Sales"].sum().sort_index()
    if weekly.empty:
        raise ValueError("No sales records were selected.")
    dates = pd.date_range(weekly.index.min(), weekly.index.max(), freq="7D")
    if not weekly.index.equals(dates):
        raise ValueError("Forecasting requires a continuous weekly history. Use the full date range and check for missing weeks.")
    return pd.DataFrame({"Sales": weekly.to_numpy()}, index=weekly.index)

def make_next_row(history, next_date):
    values = {"Date": next_date}
    for lag in LAGS:
        values[f"lag_{lag}"] = float(history.iloc[-lag])
    values["rolling_4"] = float(history.iloc[-4:].mean())
    values["rolling_8"] = float(history.iloc[-8:].mean())
    week = next_date.isocalendar().week
    values["week_sin"] = np.sin(2 * np.pi * week / 52.18)
    values["week_cos"] = np.cos(2 * np.pi * week / 52.18)
    values["trend"] = len(history)
    return pd.DataFrame([values]).set_index("Date")[FEATURES]

def recursive_forecast(model, history, steps):
    values = history.copy()
    predictions = []
    for _ in range(steps):
        next_date = values.index[-1] + pd.Timedelta(weeks=1)
        row = make_next_row(values, next_date)
        prediction = float(model.predict(row)[0])
        predictions.append({"Date": next_date, "PredictedSales": prediction})
        values.loc[next_date] = prediction
    return pd.DataFrame(predictions)

def train_sales_forecast(df, test_weeks=20, horizon=4):
    weekly = prepare_weekly(df)
    if len(weekly) < 85:
        raise ValueError("Select at least 85 continuous weeks for forecasting.")
    if test_weeks < 4 or test_weeks >= len(weekly) - 60:
        raise ValueError("Invalid test period length.")
    train_history = weekly["Sales"].iloc[:-test_weeks]
    test_actual = weekly["Sales"].iloc[-test_weeks:]
    training_features = create_features(weekly.iloc[:-test_weeks])
    model = RandomForestRegressor(n_estimators=150, max_depth=8, min_samples_leaf=2, random_state=42, n_jobs=-1)
    model.fit(training_features[FEATURES], training_features["Sales"])
    predicted = recursive_forecast(model, train_history, test_weeks)
    baseline = recursive_forecast_baseline(train_history, test_weeks)
    actual = test_actual.to_numpy()
    pred_values = predicted["PredictedSales"].to_numpy()
    baseline_values = baseline["PredictedSales"].to_numpy()
    metrics = pd.DataFrame([
        calculate_metrics("Random Forest", actual, pred_values),
        calculate_metrics("Last-week baseline", actual, baseline_values)
    ])
    evaluation = predicted.copy()
    evaluation["ActualSales"] = actual
    evaluation["BaselineSales"] = baseline_values
    full_features = create_features(weekly)
    final_model = RandomForestRegressor(n_estimators=150, max_depth=8, min_samples_leaf=2, random_state=42, n_jobs=-1)
    final_model.fit(full_features[FEATURES], full_features["Sales"])
    future = recursive_forecast(final_model, weekly["Sales"], horizon)
    return metrics, evaluation, future

def recursive_forecast_baseline(history, steps):
    next_value = float(history.iloc[-1])
    dates = [history.index[-1] + pd.Timedelta(weeks=i) for i in range(1, steps + 1)]
    return pd.DataFrame({"Date": dates, "PredictedSales": [next_value] * steps})

def calculate_metrics(name, actual, prediction):
    mae = mean_absolute_error(actual, prediction)
    rmse = np.sqrt(mean_squared_error(actual, prediction))
    denominator = np.abs(actual).sum()
    wape = np.abs(actual - prediction).sum() / denominator * 100 if denominator else np.nan
    return {"Model": name, "MAE": mae, "RMSE": rmse, "WAPE": wape}