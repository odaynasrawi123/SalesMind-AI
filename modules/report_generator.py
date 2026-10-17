from io import BytesIO
from html import escape
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch

NAVY = colors.HexColor("#172B4D")
TEAL = colors.HexColor("#0D9488")
MUTED = colors.HexColor("#64748B")
LIGHT = colors.HexColor("#F1F5F9")
RED = colors.HexColor("#DC2626")
BLUE = colors.HexColor("#2563EB")

def money(value):
    return f"${float(value):,.2f}"

def percent_change(current, previous):
    if pd.isna(previous) or previous == 0:
        return None
    return (current - previous) / abs(previous) * 100

def prepare_period(df, report_type, period):
    data = df.copy()
    data["Date"] = pd.to_datetime(data["Date"])
    data["Weekly_Sales"] = pd.to_numeric(data["Weekly_Sales"], errors="coerce")
    data = data.dropna(subset=["Date", "Weekly_Sales"])
    if data.empty:
        raise ValueError("No valid sales records are available.")
    if report_type == "Weekly":
        current = pd.Timestamp(period)
        previous = current - pd.Timedelta(weeks=1)
        current_data = data[data["Date"] == current].copy()
        previous_data = data[data["Date"] == previous].copy()
        label = f"Week ending {current:%d %B %Y}"
        previous_label = f"Week ending {previous:%d %B %Y}"
    elif report_type == "Monthly":
        current = pd.Period(period, freq="M")
        previous = current - 1
        months = data["Date"].dt.to_period("M")
        current_data = data[months == current].copy()
        previous_data = data[months == previous].copy()
        label = current.strftime("%B %Y")
        previous_label = previous.strftime("%B %Y")
    else:
        raise ValueError("Report type must be Weekly or Monthly.")
    if current_data.empty:
        raise ValueError("No sales records exist for the selected reporting period.")
    return data, current_data, previous_data, label, previous_label

def calculate_report_metrics(current, previous):
    total = float(current["Weekly_Sales"].sum())
    previous_total = float(previous["Weekly_Sales"].sum()) if not previous.empty else None
    store_weeks = current.groupby(["Store", "Date"])["Weekly_Sales"].sum()
    metrics = {
        "sales": total,
        "previous_sales": previous_total,
        "change_pct": percent_change(total, previous_total) if previous_total is not None else None,
        "stores": int(current["Store"].nunique()),
        "departments": int(current["Dept"].nunique()),
        "weeks": int(current["Date"].nunique()),
        "average_store_week": float(store_weeks.mean()) if len(store_weeks) else 0,
        "negative_rows": int((current["Weekly_Sales"] < 0).sum())
    }
    return metrics

def calculate_rankings(current):
    stores = current.groupby("Store", as_index=False).agg(Sales=("Weekly_Sales", "sum"), Weeks=("Date", "nunique"))
    stores["AverageWeeklySales"] = stores["Sales"] / stores["Weeks"]
    stores = stores.sort_values("Sales", ascending=False)
    departments = current.groupby("Dept", as_index=False)["Weekly_Sales"].sum()
    departments = departments.rename(columns={"Weekly_Sales": "Sales"}).sort_values("Sales", ascending=False)
    return stores, departments

def calculate_store_alerts(current, previous, threshold=-10):
    if previous.empty:
        return pd.DataFrame(columns=["Store", "PreviousSales", "CurrentSales", "ChangePct", "Decline"])
    current_stores = current.groupby("Store")["Weekly_Sales"].sum().rename("CurrentSales")
    previous_stores = previous.groupby("Store")["Weekly_Sales"].sum().rename("PreviousSales")
    comparison = pd.concat([current_stores, previous_stores], axis=1).dropna()
    comparison = comparison[comparison["PreviousSales"] > 0].copy()
    comparison["ChangePct"] = (comparison["CurrentSales"] - comparison["PreviousSales"]) / comparison["PreviousSales"] * 100
    comparison["Decline"] = (comparison["PreviousSales"] - comparison["CurrentSales"]).clip(lower=0)
    return comparison[comparison["ChangePct"] <= threshold].sort_values("Decline", ascending=False).reset_index()

def create_trend_chart(data, current, report_type):
    weekly = data.groupby("Date")["Weekly_Sales"].sum().sort_index()
    if report_type == "Monthly":
        trend = weekly.groupby(weekly.index.to_period("M")).sum()
        trend.index = trend.index.to_timestamp()
        trend = trend.tail(12)
        xlabel = "Month"
    else:
        trend = weekly.loc[:current["Date"].max()].tail(12)
        xlabel = "Week"
    fig, ax = plt.subplots(figsize=(9, 3.1))
    ax.plot(trend.index, trend.values, color="#0D9488", linewidth=2.5, marker="o", markersize=4)
    ax.fill_between(trend.index, trend.values, color="#0D9488", alpha=0.10)
    ax.set_title("Historical Sales Trend", fontsize=13, fontweight="bold", color="#172B4D", loc="left")
    ax.set_ylabel("Sales (USD)")
    ax.set_xlabel(xlabel)
    ax.grid(alpha=0.18)
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    return figure_to_buffer(fig)

def create_ranking_chart(stores):
    top = stores.head(8).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 3.3))
    ax.barh(["Store " + str(x) for x in top["Store"]], top["Sales"], color="#0D9488")
    ax.set_title("Top Stores by Recorded Sales", fontsize=13, fontweight="bold", color="#172B4D", loc="left")
    ax.set_xlabel("Recorded Sales (USD)")
    ax.grid(axis="x", alpha=0.15)
    fig.tight_layout()
    return figure_to_buffer(fig)

def figure_to_buffer(fig):
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buffer.seek(0)
    return buffer

def make_table(rows, widths=None, header=True):
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, LIGHT]),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#E2E8F0"))
    ]
    if header:
        commands += [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    table.setStyle(TableStyle(commands))
    return table

def page_footer(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(colors.HexColor("#E2E8F0"))
    canvas.line(40, 39, width - 40, 39)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(42, 26, "SalesMind AI | Historical Walmart Retail Analytics")
    canvas.drawRightString(width - 42, 26, f"Page {doc.page}")
    canvas.restoreState()

def generate_management_report(df, report_type, period, threshold=-10, forecast_metrics=None, forecast_future=None):
    data, current, previous, label, previous_label = prepare_period(df, report_type, period)
    metrics = calculate_report_metrics(current, previous)
    stores, departments = calculate_rankings(current)
    alerts = calculate_store_alerts(current, previous, threshold)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=43, leftMargin=43, topMargin=48, bottomMargin=55)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BrandSM", parent=styles["Title"], fontSize=24, leading=30, textColor=NAVY, spaceAfter=9))
    styles.add(ParagraphStyle(name="HeadingSM", parent=styles["Heading2"], fontSize=13, textColor=NAVY, spaceBefore=14, spaceAfter=9))
    styles.add(ParagraphStyle(name="BodySM", parent=styles["BodyText"], fontSize=9.5, leading=15, textColor=NAVY, spaceAfter=8))
    styles.add(ParagraphStyle(name="SmallSM", parent=styles["BodyText"], fontSize=8, leading=12, textColor=MUTED))
    story = []

    def add_heading(text):
        story.append(Paragraph(escape(text), styles["HeadingSM"]))

    def add_body(text):
        story.append(Paragraph(escape(str(text)), styles["BodySM"]))

    story.append(Paragraph("SalesMind AI", styles["BrandSM"]))
    add_body(f"{report_type.upper()} BUSINESS PERFORMANCE REPORT")
    add_body(f"Reporting period: {label}")
    add_body(f"Store coverage: {metrics['stores']} stores | {metrics['departments']} departments | USD")
    story.append(Spacer(1, 10))

    add_heading("1. Executive Summary")
    change = f"{metrics['change_pct']:+.2f}%" if metrics["change_pct"] is not None else "Not available"
    rows = [
        ["Performance Metric", "Recorded Value"],
        ["Sales in reporting period", money(metrics["sales"])],
        ["Previous comparable period", money(metrics["previous_sales"]) if metrics["previous_sales"] is not None else "No records"],
        ["Change vs previous period", change],
        ["Active stores", str(metrics["stores"])],
        ["Departments", str(metrics["departments"])],
        ["Average sales per observed store-week", money(metrics["average_store_week"])],
        ["Negative sales records", str(metrics["negative_rows"])]
    ]
    story.append(make_table(rows, [295, 210]))
    story.append(Spacer(1, 12))

    add_heading("2. Executive Findings")
    add_body(f"Recorded sales were {money(metrics['sales'])} during {label}.")
    if metrics["change_pct"] is not None:
        add_body(f"Sales changed by {metrics['change_pct']:+.2f}% compared with {previous_label}.")
    else:
        add_body("A comparable previous-period result was not available in the selected dataset.")
    if not stores.empty:
        best_store = stores.iloc[0]
        add_body(f"Store {int(best_store['Store'])} recorded the highest sales in this period: {money(best_store['Sales'])}.")
    if not departments.empty:
        best_dept = departments.iloc[0]
        add_body(f"Department {int(best_dept['Dept'])} recorded the highest departmental sales: {money(best_dept['Sales'])}.")
    if not alerts.empty:
        add_body(f"{len(alerts)} stores had declines of at least {abs(threshold):.0f}% against the previous comparable period.")
    else:
        add_body("No stores crossed the selected decline threshold among those with comparable records.")

    add_heading("3. Sales Performance")
    trend_image = create_trend_chart(data.loc[data["Date"] <= current["Date"].max()], current, report_type)
    story.append(Image(trend_image, width=490, height=185))
    story.append(Spacer(1, 10))

    add_heading("4. Store Performance")
    ranking_image = create_ranking_chart(stores)
    story.append(Image(ranking_image, width=490, height=185))
    top_store_rows = [["Store", "Recorded Sales", "Avg. Weekly Sales"]]
    for _, row in stores.head(10).iterrows():
        top_store_rows.append([str(int(row["Store"])), money(row["Sales"]), money(row["AverageWeeklySales"])])
    story.append(make_table(top_store_rows, [100, 200, 205]))

    add_heading("5. Department Performance")
    dept_rows = [["Department", "Recorded Sales"]]
    for _, row in departments.head(10).iterrows():
        dept_rows.append([str(int(row["Dept"])), money(row["Sales"])])
    story.append(make_table(dept_rows, [200, 305]))

    add_heading("6. Store Performance Alerts")
    if alerts.empty:
        add_body("No store met the decline threshold with positive previous-period sales and valid comparisons.")
    else:
        alert_rows = [["Store", "Previous Sales", "Current Sales", "Change"]]
        for _, row in alerts.head(12).iterrows():
            alert_rows.append([str(int(row["Store"])), money(row["PreviousSales"]), money(row["CurrentSales"]), f"{row['ChangePct']:.1f}%"])
        story.append(make_table(alert_rows, [65, 155, 155, 130]))

    add_heading("7. Holiday and Reporting Context")
    holiday_weeks = current[["Store", "Date", "IsHoliday"]].drop_duplicates()
    flagged = int(holiday_weeks["IsHoliday"].sum())
    add_body(f"Flagged holiday store-weeks: {flagged} of {len(holiday_weeks)} observed store-weeks.")
    add_body(f"The selected reporting period contains {metrics['weeks']} distinct weekly dates. Monthly totals assign each complete weekly observation to the calendar month of its recorded week date.")

    if forecast_metrics is not None and not forecast_metrics.empty:
        add_heading("8. Optional Forecast Evaluation")
        forecast_rows = [["Model", "MAE", "RMSE", "WAPE"]]
        for _, row in forecast_metrics.iterrows():
            forecast_rows.append([str(row["Model"]), money(row["MAE"]), money(row["RMSE"]), f"{row['WAPE']:.2f}%"])
        story.append(make_table(forecast_rows, [175, 115, 115, 100]))
        if forecast_future is not None and not forecast_future.empty:
            add_body("Forecasted weeks: " + ", ".join(f"{pd.Timestamp(row['Date']):%Y-%m-%d}: {money(row['PredictedSales'])}" for _, row in forecast_future.iterrows()))
        add_body("Forecasts are estimates, and the historical test metrics do not guarantee future accuracy.")

    add_heading("Data Source and Limitations")
    add_body("Source: Walmart Recruiting - Store Sales Forecasting (Kaggle), historical training data from 2010-2012.")
    add_body("This report uses recorded store-department weekly sales from the selected dashboard filters. Sales do not represent profit. No customer-level or product-level data are available.")
    add_body("Negative weekly sales values are retained. Alert thresholds are descriptive, not proof of operational problems. Comparisons can be affected by calendar composition, selected departments and incomplete reporting periods.")
    add_body("Reports are intended for exploratory business intelligence and demonstration purposes.")
    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    buffer.seek(0)
    return buffer.getvalue()