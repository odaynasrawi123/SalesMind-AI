import pandas as pd

def business_kpis(df):
    result = {
        "NetRecordedSales": float(df["Revenue"].sum()),
        "PositiveSales": float(df["Revenue"].clip(lower=0).sum()),
        "NegativeAdjustments": float(-df["Revenue"].clip(upper=0).sum()),
        "Transactions": len(df),
        "Orders": None,
        "Customers": None,
        "Products": None,
        "Stores": None,
        "Units": None,
        "AOV": None
    }
    if "OrderID" in df:
        result["Orders"] = int(df["OrderID"].nunique())
        positive = df[df["Revenue"] > 0]
        orders = positive["OrderID"].nunique()
        result["AOV"] = float(positive["Revenue"].sum() / orders) if orders else None
    if "CustomerID" in df:
        result["Customers"] = int(df["CustomerID"].nunique())
    if "Product" in df:
        result["Products"] = int(df["Product"].nunique())
    if "Store" in df:
        result["Stores"] = int(df["Store"].nunique())
    if "Quantity" in df:
        result["Units"] = float(df["Quantity"].sum())
    return result

def business_trend(df, frequency="D"):
    result = df.set_index("Date").resample(frequency)["Revenue"].sum().reset_index()
    return result.rename(columns={"Revenue": "Sales"})

def business_breakdown(df, column, limit=20):
    if column not in df:
        return pd.DataFrame(columns=[column, "Sales", "Rows"])
    result = df.dropna(subset=[column]).groupby(column, as_index=False).agg(Sales=("Revenue", "sum"), Rows=("Revenue", "size"))
    return result.sort_values("Sales", ascending=False).head(limit)

def business_customer_analysis(df):
    if "CustomerID" not in df:
        return None
    data = df.dropna(subset=["CustomerID"]).copy()
    if "OrderID" in data:
        customers = data.groupby("CustomerID", as_index=False).agg(Sales=("Revenue", "sum"), Orders=("OrderID", "nunique"), LastPurchase=("Date", "max"))
    else:
        customers = data.groupby("CustomerID", as_index=False).agg(Sales=("Revenue", "sum"), Records=("Revenue", "size"), LastPurchase=("Date", "max"))
    return customers.sort_values("Sales", ascending=False)

def business_monthly_growth(df):
    monthly = business_trend(df, "MS")
    monthly["PreviousSales"] = monthly["Sales"].shift(1)
    monthly["GrowthPct"] = (monthly["Sales"] - monthly["PreviousSales"]) / monthly["PreviousSales"].abs().replace(0, float("nan")) * 100
    return monthly

def business_findings(df):
    findings = []
    if df.empty:
        return ["No valid records match the selected filters."]
    kpis = business_kpis(df)
    findings.append(f"Total recorded net sales: {kpis['NetRecordedSales']:,.2f}.")
    for field, label in [("Store", "store"), ("Category", "category"), ("Product", "product")]:
        if field in df:
            result = business_breakdown(df, field, 1)
            if not result.empty:
                row = result.iloc[0]
                findings.append(f"Highest recorded sales by {label}: {row[field]} ({row['Sales']:,.2f}).")
    if kpis["NegativeAdjustments"] > 0:
        findings.append(f"Negative sales or adjustments total {kpis['NegativeAdjustments']:,.2f}. Their underlying causes are not identified.")
    return findings