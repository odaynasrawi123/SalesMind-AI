import numpy as np
import pandas as pd
import pytest

@pytest.fixture
def sample_walmart():
    dates = pd.date_range("2010-02-05", periods=110, freq="7D")
    rows = []
    for week, date in enumerate(dates):
        for store in [1, 2]:
            for dept in [1, 2]:
                sales = 10000 + store * 1200 + dept * 400 + 300 * np.sin(week / 4) + week * 15
                rows.append({"Store": store, "Dept": dept, "Date": date, "Weekly_Sales": float(sales), "IsHoliday": week % 13 == 0, "Type": "A" if store == 1 else "B", "Size": 120000 if store == 1 else 90000})
    return pd.DataFrame(rows)

@pytest.fixture
def raw_walmart(sample_walmart):
    train = sample_walmart[["Store", "Dept", "Date", "Weekly_Sales", "IsHoliday"]].copy()
    features = sample_walmart[["Store", "Date", "IsHoliday"]].drop_duplicates().copy()
    for column in ["Temperature", "Fuel_Price", "CPI", "Unemployment"]:
        features[column] = 1.0
    for i in range(1, 6):
        features[f"MarkDown{i}"] = 0.0
    stores = sample_walmart[["Store", "Type", "Size"]].drop_duplicates().copy()
    return train, features, stores