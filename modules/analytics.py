import pandas as pd

def calculate_kpis(df):
    sales = df["Weekly_Sales"].sum()
    stores = df["Store"].nunique()
    departments = df["Dept"].nunique()
    weeks = df["Date"].nunique()
    store_weeks = df.groupby(["Store", "Date"])["Weekly_Sales"].sum()
    return {
        "Total Sales": sales,
        "Stores": stores,
        "Departments": departments,
        "Weeks": weeks,
        "Average Store-Week Sales": store_weeks.mean() if len(store_weeks) else 0,
        "Negative Sales Rows": int((df["Weekly_Sales"] < 0).sum())
    }

def weekly_sales(df):
    return df.groupby("Date", as_index=False)["Weekly_Sales"].sum().sort_values("Date")

def monthly_sales(df):
    return df.groupby("Month", as_index=False)["Weekly_Sales"].sum().sort_values("Month")

def store_performance(df):
    result = df.groupby(["Store", "Type", "Size"], as_index=False).agg(TotalSales=("Weekly_Sales", "sum"), Weeks=("Date", "nunique"), Departments=("Dept", "nunique"))
    result["AverageWeeklySales"] = result["TotalSales"] / result["Weeks"].replace(0, float("nan"))
    return result.sort_values("TotalSales", ascending=False)

def department_performance(df):
    result = df.groupby("Dept", as_index=False).agg(TotalSales=("Weekly_Sales", "sum"), Stores=("Store", "nunique"), Weeks=("Date", "nunique"))
    return result.sort_values("TotalSales", ascending=False)

def store_weekly_sales(df):
    return df.groupby(["Store", "Date"], as_index=False)["Weekly_Sales"].sum()

def holiday_performance(df):
    store_week = df.groupby(["Store", "Date", "IsHoliday"], as_index=False)["Weekly_Sales"].sum()
    return store_week.groupby("IsHoliday", as_index=False).agg(AverageStoreWeekSales=("Weekly_Sales", "mean"), TotalSales=("Weekly_Sales", "sum"), StoreWeeks=("Weekly_Sales", "size"))

def store_type_performance(df):
    store_week = df.groupby(["Store", "Type", "Date"], as_index=False)["Weekly_Sales"].sum()
    return store_week.groupby("Type", as_index=False).agg(TotalSales=("Weekly_Sales", "sum"), AverageStoreWeekSales=("Weekly_Sales", "mean"), StoreWeeks=("Weekly_Sales", "size"), Stores=("Store", "nunique"))

def sales_growth(df):
    result = weekly_sales(df)
    result["PreviousWeek"] = result["Weekly_Sales"].shift(1)
    result["GrowthPct"] = (result["Weekly_Sales"] - result["PreviousWeek"]) / result["PreviousWeek"].abs().replace(0, float("nan")) * 100
    return result

def export_summary(df):
    stores = store_performance(df)
    departments = department_performance(df)
    return stores, departments