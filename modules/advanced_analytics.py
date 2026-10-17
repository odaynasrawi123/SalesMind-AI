import pandas as pd

def best_worst_stores(df, n=10):
    result = df.groupby(["Store", "Type"], as_index=False).agg(TotalSales=("Weekly_Sales", "sum"), Weeks=("Date", "nunique"))
    result["AverageWeeklySales"] = result["TotalSales"] / result["Weeks"]
    result = result.sort_values("AverageWeeklySales", ascending=False)
    return result.head(n), result.tail(n).sort_values("AverageWeeklySales")

def department_store_matrix(df):
    result = df.groupby(["Store", "Dept"])["Weekly_Sales"].sum().unstack(fill_value=0)
    return result

def holiday_comparison(df):
    store_week = df.groupby(["Store", "Date", "IsHoliday"], as_index=False)["Weekly_Sales"].sum()
    comparison = store_week.groupby("IsHoliday")["Weekly_Sales"].agg(["mean", "median", "count"]).reset_index()
    comparison.columns = ["IsHoliday", "AverageSales", "MedianSales", "StoreWeeks"]
    return comparison

def markdown_analysis(df):
    columns = [f"MarkDown{i}" for i in range(1, 6) if f"MarkDown{i}" in df.columns]
    if not columns:
        return pd.DataFrame()
    weekly = df.groupby(["Store", "Date"], as_index=False).agg({"Weekly_Sales": "sum", **{c: "first" for c in columns}})
    result = []
    for column in columns:
        valid = weekly[["Weekly_Sales", column]].dropna()
        result.append({"MarkDown": column, "AvailableStoreWeeks": len(valid), "Correlation": valid["Weekly_Sales"].corr(valid[column]) if len(valid) > 2 and valid[column].nunique() > 1 else float("nan")})
    return pd.DataFrame(result)

def economic_indicators(df):
    columns = ["Temperature", "Fuel_Price", "CPI", "Unemployment"]
    available = [c for c in columns if c in df.columns]
    aggregations = {"Weekly_Sales": "sum"}
    aggregations.update({c: "first" for c in available})
    return df.groupby(["Store", "Date"], as_index=False).agg(aggregations)

def generate_insights(df):
    insights = []
    if df.empty:
        return ["No records match the selected filters."]
    stores = df.groupby(["Store", "Date"], as_index=False)["Weekly_Sales"].sum()
    totals = stores.groupby("Store")["Weekly_Sales"].sum().sort_values(ascending=False)
    if not totals.empty:
        insights.append(f"Store {int(totals.index[0])} generated the highest total recorded sales: ${totals.iloc[0]:,.0f}.")
    dept = df.groupby("Dept")["Weekly_Sales"].sum().sort_values(ascending=False)
    if not dept.empty:
        insights.append(f"Department {int(dept.index[0])} recorded the highest aggregate sales: ${dept.iloc[0]:,.0f}.")
    comparison = holiday_comparison(df).set_index("IsHoliday")
    if True in comparison.index and False in comparison.index:
        regular = comparison.loc[False, "AverageSales"]
        holiday = comparison.loc[True, "AverageSales"]
        if regular != 0:
            change = (holiday - regular) / abs(regular) * 100
            insights.append(f"Observed average store-week sales were {change:+.1f}% different during flagged holiday weeks. This is an association, not proof of a holiday effect.")
    negatives = int((df["Weekly_Sales"] < 0).sum())
    insights.append(f"{negatives:,} store-department-week records contain negative sales and remain included in the totals.")
    return insights