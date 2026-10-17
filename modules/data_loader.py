from pathlib import Path
import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

@st.cache_data(show_spinner="Loading Walmart sales data...")
def load_data():
    paths = {name: DATA_DIR / f"{name}.csv" for name in ["train", "features", "stores"]}
    for name, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing {name}.csv in {DATA_DIR}")
    train = pd.read_csv(paths["train"], parse_dates=["Date"])
    features = pd.read_csv(paths["features"], parse_dates=["Date"])
    stores = pd.read_csv(paths["stores"])
    expected = {
        "train": {"Store", "Dept", "Date", "Weekly_Sales", "IsHoliday"},
        "features": {"Store", "Date", "IsHoliday", "Temperature", "Fuel_Price", "CPI", "Unemployment"},
        "stores": {"Store", "Type", "Size"}
    }
    for name, frame in [("train", train), ("features", features), ("stores", stores)]:
        missing = expected[name] - set(frame.columns)
        if missing:
            raise ValueError(f"{name}.csv missing columns: {sorted(missing)}")
    return train, features, stores

@st.cache_data(show_spinner="Preparing Walmart transactions...")
def clean_data(train, features, stores):
    sales = train.copy()
    feature_data = features.copy()
    store_data = stores.copy()
    sales["Weekly_Sales"] = pd.to_numeric(sales["Weekly_Sales"], errors="coerce")
    sales["Date"] = pd.to_datetime(sales["Date"], errors="coerce")
    sales = sales.dropna(subset=["Store", "Dept", "Date", "Weekly_Sales"])
    sales["Store"] = sales["Store"].astype(int)
    sales["Dept"] = sales["Dept"].astype(int)
    sales = sales.drop_duplicates(subset=["Store", "Dept", "Date"], keep="last")
    for frame in [sales, feature_data]:
        frame["IsHoliday"] = frame["IsHoliday"].astype("string").str.lower().eq("true")
    feature_data = feature_data.drop(columns=["IsHoliday"])
    if feature_data.duplicated(["Store", "Date"]).any():
        raise ValueError("Duplicate Store-Date keys in features.csv")
    if store_data.duplicated("Store").any():
        raise ValueError("Duplicate Store IDs in stores.csv")
    data = sales.merge(feature_data, on=["Store", "Date"], how="left", validate="many_to_one")
    data = data.merge(store_data, on="Store", how="left", validate="many_to_one")
    if data["Type"].isna().any():
        raise ValueError("Some stores have no matching record in stores.csv")
    data["Month"] = data["Date"].dt.to_period("M").dt.to_timestamp()
    data["Year"] = data["Date"].dt.year
    data["Week"] = data["Date"].dt.isocalendar().week.astype(int)
    data["HolidayType"] = data["IsHoliday"].map({True: "Holiday", False: "Regular"})
    data["SalesStatus"] = data["Weekly_Sales"].ge(0).map({True: "Nonnegative", False: "Negative adjustment"})
    data["StoreLabel"] = "Store " + data["Store"].astype(str)
    data["DepartmentLabel"] = "Department " + data["Dept"].astype(str)
    return data.sort_values(["Date", "Store", "Dept"]).reset_index(drop=True)