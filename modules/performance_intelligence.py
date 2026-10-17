import pandas as pd
import numpy as np

def weekly_comparison(df):
    weekly = df.groupby("Date")["Weekly_Sales"].sum().sort_index()
    if len(weekly) < 2:
        return {"CurrentSales": None, "PreviousSales": None, "WoW": None, "YoY": None, "Date": None}
    current_date = weekly.index[-1]
    current = float(weekly.iloc[-1])
    previous = float(weekly.iloc[-2])
    last_year_date = current_date - pd.Timedelta(weeks=52)
    last_year = weekly.get(last_year_date, np.nan)
    wow = (current - previous) / abs(previous) * 100 if previous != 0 else np.nan
    yoy = (current - last_year) / abs(last_year) * 100 if pd.notna(last_year) and last_year != 0 else np.nan
    return {"CurrentSales": current, "PreviousSales": previous, "WoW": wow, "YoY": yoy, "Date": current_date}

def performance_alerts(df, threshold=-10):
    weekly = df.groupby(["Store", "Date"], as_index=False)["Weekly_Sales"].sum()
    dates = sorted(weekly["Date"].unique())
    if len(dates) < 2:
        return pd.DataFrame()
    current_date, previous_date = dates[-1], dates[-2]
    current = weekly[weekly["Date"] == current_date][["Store", "Weekly_Sales"]].rename(columns={"Weekly_Sales": "CurrentSales"})
    previous = weekly[weekly["Date"] == previous_date][["Store", "Weekly_Sales"]].rename(columns={"Weekly_Sales": "PreviousSales"})
    result = current.merge(previous, on="Store", how="inner")
    result = result[result["PreviousSales"] > 0].copy()
    result["ChangePct"] = (result["CurrentSales"] - result["PreviousSales"]) / result["PreviousSales"] * 100
    result["RevenueDecline"] = (result["PreviousSales"] - result["CurrentSales"]).clip(lower=0)
    result["Status"] = np.where(result["ChangePct"] <= threshold, "Attention", "Normal")
    return result.sort_values(["RevenueDecline", "ChangePct"], ascending=[False, True])

def department_alerts(df, threshold=-10):
    weekly = df.groupby(["Store", "Dept", "Date"], as_index=False)["Weekly_Sales"].sum()
    dates = sorted(weekly["Date"].unique())
    if len(dates) < 2:
        return pd.DataFrame()
    current = weekly[weekly["Date"] == dates[-1]][["Store", "Dept", "Weekly_Sales"]].rename(columns={"Weekly_Sales": "CurrentSales"})
    previous = weekly[weekly["Date"] == dates[-2]][["Store", "Dept", "Weekly_Sales"]].rename(columns={"Weekly_Sales": "PreviousSales"})
    result = current.merge(previous, on=["Store", "Dept"], how="inner")
    result = result[result["PreviousSales"] > 0].copy()
    result["ChangePct"] = (result["CurrentSales"] - result["PreviousSales"]) / result["PreviousSales"] * 100
    result["RevenueDecline"] = (result["PreviousSales"] - result["CurrentSales"]).clip(lower=0)
    return result[result["ChangePct"] <= threshold].sort_values("RevenueDecline", ascending=False)

def executive_findings(df, threshold=-10):
    findings = []
    comparison = weekly_comparison(df)
    if comparison["WoW"] is not None and pd.notna(comparison["WoW"]):
        findings.append(f"Latest weekly sales changed by {comparison['WoW']:+.2f}% compared with the previous available week.")
    if comparison["YoY"] is not None and pd.notna(comparison["YoY"]):
        findings.append(f"Sales changed by {comparison['YoY']:+.2f}% compared with 52 weeks earlier.")
    alerts = performance_alerts(df, threshold)
    if not alerts.empty:
        affected = alerts[alerts["Status"] == "Attention"]
        findings.append(f"{len(affected)} stores recorded sales declines of at least {abs(threshold):.0f}% compared with the previous available week.")
        if not affected.empty:
            top = affected.iloc[0]
            findings.append(f"Store {int(top['Store'])} had the largest monetary decline among flagged stores: ${top['RevenueDecline']:,.0f}.")
    if not findings:
        findings.append("Not enough comparable observations to calculate performance changes.")
    return findings