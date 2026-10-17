import streamlit as st
import pandas as pd
import plotly.express as px
from modules.data_loader import load_data, clean_data
from modules.analytics import calculate_kpis, weekly_sales, store_performance, department_performance, store_weekly_sales, store_type_performance
from modules.advanced_analytics import best_worst_stores, department_store_matrix, holiday_comparison, markdown_analysis, economic_indicators, generate_insights
from modules.performance_intelligence import weekly_comparison, performance_alerts, department_alerts, executive_findings
from modules.forecasting import train_sales_forecast
from modules.ui import apply_styles, page_header, section_title, money, metric_card, show_chart, insight_card
from modules.report_generator import generate_management_report
from modules.data_validation import validate_raw_data, validate_clean_data, store_week_coverage, reporting_period_coverage, reconcile_report_kpis, health_summary
from modules.backtesting import backtest_sales, summarize_backtesting
from modules.business_workspace import render_business_workspace



st.set_page_config(page_title="SalesMind AI | Enterprise Dashboard", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
apply_styles()
page_header("Business Intelligence Dashboard", "Monitor sales, compare stores, identify risks and forecast performance.")

# Load Walmart dataset
try:
    train, features, stores = load_data()
    df = clean_data(train, features, stores)
except Exception as error:
    st.error(f"Dataset loading error: {error}")
    st.stop()

# Sidebar
st.sidebar.title("◈ SalesMind")
st.sidebar.caption("ENTERPRISE RETAIL INTELLIGENCE")
st.sidebar.divider()
st.sidebar.markdown("### Dashboard Filters")

all_stores = sorted(df["Store"].unique().tolist())
all_types = sorted(df["Type"].unique().tolist())
all_depts = sorted(df["Dept"].unique().tolist())

selected_stores = st.sidebar.multiselect("Stores", all_stores, default=all_stores)
selected_types = st.sidebar.multiselect("Store Types", all_types, default=all_types)
selected_depts = st.sidebar.multiselect("Departments", all_depts, default=all_depts)
date_range = st.sidebar.date_input("Date Range", value=(df["Date"].min().date(), df["Date"].max().date()))

if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    st.info("Please select both start and end dates.")
    st.stop()

start_date, end_date = date_range
filtered = df[df["Store"].isin(selected_stores) & df["Type"].isin(selected_types) & df["Dept"].isin(selected_depts)].copy()
filtered = filtered[filtered["Date"].dt.date.between(start_date, end_date)].copy()

if filtered.empty:
    st.warning("No records match your filters.")
    st.stop()

# Sidebar summary - after filtered is defined
st.sidebar.divider()
st.sidebar.markdown("### Current Selection")
st.sidebar.caption(f"Stores: {filtered['Store'].nunique()}")
st.sidebar.caption(f"Departments: {filtered['Dept'].nunique()}")
st.sidebar.caption(f"Weeks: {filtered['Date'].nunique()}")
st.sidebar.caption(f"Period: {start_date} → {end_date}")
st.sidebar.caption(f"Records: {len(filtered):,}")
st.sidebar.divider()
st.sidebar.caption("Walmart Historical Dataset")
st.sidebar.caption("Currency: USD | 2010–2012")

tabs = st.tabs(["Executive Overview", "Store Performance", "Departments", "Holiday Analytics", "External Factors", "Data Explorer", "Performance Intelligence", "Management Reports", "System Health", "Business Workspace"])


# TAB 0 - Executive Overview
with tabs[0]:
    section_title("Executive Overview")
    kpis = calculate_kpis(filtered)
    comparison = weekly_comparison(filtered)
    wow = comparison["WoW"]
    yoy = comparison["YoY"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Total Recorded Sales", money(kpis["Total Sales"]))
    with c2:
        metric_card("Average Store-Week", money(kpis["Average Store-Week Sales"]))
    with c3:
        metric_card("Active Stores", f"{kpis['Stores']:,}")
    with c4:
        metric_card("Departments", f"{kpis['Departments']:,}")

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        metric_card("Latest Weekly Sales", money(comparison["CurrentSales"]) if comparison["CurrentSales"] is not None else "N/A", f"{wow:+.1f}%" if wow is not None and pd.notna(wow) else None)
    with c6:
        metric_card("Year-over-Year Change", f"{yoy:+.2f}%" if yoy is not None and pd.notna(yoy) else "N/A")
    with c7:
        metric_card("Weeks Tracked", f"{kpis['Weeks']:,}")
    with c8:
        metric_card("Negative Sales Records", f"{kpis['Negative Sales Rows']:,}")

    st.divider()
    section_title("Weekly Sales Performance")
    weekly = weekly_sales(filtered)
    fig = px.area(weekly, x="Date", y="Weekly_Sales", color_discrete_sequence=["#0D9488"])
    fig.update_traces(line=dict(width=2.5), fillcolor="rgba(13,148,136,0.12)")
    fig.update_layout(xaxis_title="Week", yaxis_title="Recorded Sales ($)")
    show_chart(fig, "Historical Weekly Sales", 430)

    left, right = st.columns(2)
    with left:
        section_title("Top Performing Stores")
        top_stores = store_performance(filtered).head(10).copy()
        top_stores["StoreLabel"] = "Store " + top_stores["Store"].astype(str)
        fig = px.bar(top_stores, x="TotalSales", y="StoreLabel", orientation="h", color_discrete_sequence=["#0D9488"])
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, xaxis_title="Recorded Sales ($)", yaxis_title="")
        show_chart(fig, "Top 10 Stores by Recorded Sales", 430)

    with right:
        section_title("Store Type Performance")
        types = store_type_performance(filtered)
        fig = px.bar(types, x="Type", y="AverageStoreWeekSales", color="Type", color_discrete_sequence=["#0D9488", "#2563EB", "#8B5CF6"])
        fig.update_layout(xaxis_title="Store Type", yaxis_title="Average Store-Week Sales ($)", showlegend=False)
        show_chart(fig, "Average Sales by Store Type", 430)

    st.divider()
    section_title("Executive Business Findings")
    for finding in generate_insights(filtered):
        insight_card("Business Observation", finding)

# TAB 1 - Store Performance
with tabs[1]:
    section_title("Store Performance")
    st.caption("Compare historical sales across Walmart stores.")

    performance = store_performance(filtered)
    ranking_metric = st.selectbox("Rank stores by", ["TotalSales", "AverageWeeklySales"], key="store_ranking")
    ranking = performance.sort_values(ranking_metric, ascending=False).copy()
    ranking["StoreLabel"] = "Store " + ranking["Store"].astype(str)

    fig = px.bar(ranking, x="StoreLabel", y=ranking_metric, color="Type", color_discrete_sequence=["#0D9488", "#2563EB", "#8B5CF6"])
    fig.update_layout(xaxis_title="Store", yaxis_title="Sales ($)", xaxis_tickangle=-45)
    show_chart(fig, f"Store Ranking — {ranking_metric}", 490)

    st.divider()
    section_title("Compare Stores Over Time")
    available_stores = sorted(filtered["Store"].unique().tolist())
    chosen_stores = st.multiselect("Select stores to compare", available_stores, default=available_stores[:3], key="store_comparison")
    comparison_data = store_weekly_sales(filtered)
    comparison_data = comparison_data[comparison_data["Store"].isin(chosen_stores)].copy()

    if not comparison_data.empty:
        comparison_data["StoreLabel"] = "Store " + comparison_data["Store"].astype(str)
        fig = px.line(comparison_data, x="Date", y="Weekly_Sales", color="StoreLabel")
        fig.update_layout(xaxis_title="Week", yaxis_title="Recorded Sales ($)")
        show_chart(fig, "Weekly Sales by Selected Stores", 470)
    else:
        st.info("Select at least one store to display a comparison.")

    st.divider()
    left, right = st.columns(2)
    best, worst = best_worst_stores(filtered)

    with left:
        section_title("Highest Average Weekly Sales")
        st.dataframe(best.round(2), use_container_width=True, hide_index=True)

    with right:
        section_title("Lowest Average Weekly Sales")
        st.dataframe(worst.round(2), use_container_width=True, hide_index=True)

    section_title("Complete Store Performance")
    st.dataframe(performance.round(2), use_container_width=True, hide_index=True)
    st.caption("Store rankings reflect the selected filters. Store size, assortment and recorded weeks may differ.")

# TAB 2 - Departments
with tabs[2]:
    section_title("Department Intelligence")
    st.caption("Identify the highest-revenue departments and compare their performance between stores.")

    departments = department_performance(filtered)
    c1, c2 = st.columns(2)
    with c1:
        metric_card("Departments Represented", f"{len(departments):,}")
    with c2:
        metric_card("Recorded Department Sales", money(departments["TotalSales"].sum()))

    st.divider()
    top_n = st.slider("Number of departments to display", 5, 30, 15, key="department_top_n")
    top_depts = departments.head(top_n).copy()
    top_depts["DepartmentLabel"] = "Dept " + top_depts["Dept"].astype(str)

    fig = px.bar(top_depts, x="DepartmentLabel", y="TotalSales", color_discrete_sequence=["#0D9488"])
    fig.update_layout(xaxis_title="Department", yaxis_title="Recorded Sales ($)")
    show_chart(fig, f"Top {top_n} Revenue Departments", 450)

    st.divider()
    section_title("Store-Department Sales Heatmap")
    matrix = department_store_matrix(filtered)

    if not matrix.empty:
        fig = px.imshow(matrix, aspect="auto", color_continuous_scale="Teal", labels={"x": "Department", "y": "Store", "color": "Sales ($)"})
        show_chart(fig, "Recorded Sales by Store and Department", 620)

    st.divider()
    section_title("Department Rankings")
    st.dataframe(departments.round(2), use_container_width=True, hide_index=True)
    st.caption("Department IDs are anonymized. Individual products are not available in this dataset.")

# TAB 3 - Holiday Analytics
with tabs[3]:
    section_title("Holiday Sales Analytics")
    st.caption("Compare flagged holiday weeks with regular weeks.")

    holiday_data = holiday_comparison(filtered).copy()
    holiday_data["WeekType"] = holiday_data["IsHoliday"].map({True: "Holiday", False: "Regular"})

    fig = px.bar(holiday_data, x="WeekType", y="AverageSales", color="WeekType", color_discrete_map={"Holiday": "#0D9488", "Regular": "#2563EB"})
    fig.update_layout(xaxis_title="Week Type", yaxis_title="Average Store-Week Sales ($)", showlegend=False)
    show_chart(fig, "Holiday vs Regular Week Sales", 430)

    st.dataframe(holiday_data.round(2), use_container_width=True, hide_index=True)

    st.divider()
    section_title("Holiday Weekly Sales")
    holiday_weekly = filtered.groupby(["Date", "IsHoliday"], as_index=False)["Weekly_Sales"].sum()
    holiday_only = holiday_weekly[holiday_weekly["IsHoliday"]].copy()

    if not holiday_only.empty:
        fig = px.bar(holiday_only, x="Date", y="Weekly_Sales", color_discrete_sequence=["#0D9488"])
        fig.update_layout(xaxis_title="Holiday Week", yaxis_title="Recorded Sales ($)")
        show_chart(fig, "Total Sales During Flagged Holiday Weeks", 450)
    else:
        st.info("No holiday weeks match the selected filters.")

    st.caption("Holiday differences are observational; they do not establish that holidays caused the changes.")

# TAB 4 - External Factors
with tabs[4]:
    section_title("Economic & Promotional Indicators")
    st.caption("Explore associations between store sales, economic indicators and promotional markdowns.")

    economy = economic_indicators(filtered)
    indicator = st.selectbox("Choose an economic indicator", ["Temperature", "Fuel_Price", "CPI", "Unemployment"])
    plot_data = economy.dropna(subset=[indicator, "Weekly_Sales"]).copy()

    if not plot_data.empty:
        plot_data["StoreLabel"] = "Store " + plot_data["Store"].astype(str)
        fig = px.scatter(plot_data, x=indicator, y="Weekly_Sales", color="StoreLabel", opacity=0.5)
        fig.update_layout(xaxis_title=indicator, yaxis_title="Store-Week Sales ($)")
        show_chart(fig, f"Store Sales vs {indicator}", 520)
    else:
        st.info("No valid data for the selected economic indicator.")

    st.divider()
    section_title("Promotional Markdown Analysis")
    markdowns = markdown_analysis(filtered)

    if not markdowns.empty:
        fig = px.bar(markdowns, x="MarkDown", y="Correlation", color_discrete_sequence=["#0D9488"])
        fig.update_layout(xaxis_title="Markdown Feature", yaxis_title="Correlation")
        show_chart(fig, "Markdown vs Store-Week Sales Correlation", 440)
        st.dataframe(markdowns.round(3), use_container_width=True, hide_index=True)
    else:
        st.info("No markdown information is available.")

    st.caption("Correlations are not causal effects. Missing markdown values are preserved.")

# TAB 5 - Data Explorer
with tabs[5]:
    section_title("Data Explorer")
    st.caption("Inspect and export the underlying Walmart dataset.")

    summary = pd.DataFrame({
        "Metric": ["Original Sales Rows", "Filtered Rows", "Active Stores", "Departments", "Weeks", "Negative Sales Records"],
        "Value": [len(train), len(filtered), filtered["Store"].nunique(), filtered["Dept"].nunique(), filtered["Date"].nunique(), int((filtered["Weekly_Sales"] < 0).sum())]
    })

    section_title("Dataset Summary")
    st.dataframe(summary, use_container_width=True, hide_index=True)

    section_title("Missing Values")
    missing = filtered.isna().sum().reset_index()
    missing.columns = ["Column", "Missing Values"]
    missing["Missing Percent"] = missing["Missing Values"] / len(filtered) * 100
    st.dataframe(missing.round(2), use_container_width=True, hide_index=True)

    section_title("Transaction Records")
    st.dataframe(filtered.head(2000), use_container_width=True, hide_index=True)
    st.caption("Showing the first 2,000 selected records. Download the CSV for all selected records.")

    csv_data = filtered.to_csv(index=False).encode("utf-8")
    st.download_button("Download Filtered Sales CSV", data=csv_data, file_name="salesmind_walmart_filtered.csv", mime="text/csv")
# TAB 6 - Performance Intelligence
with tabs[6]:
    section_title("Business Performance Intelligence")
    st.caption("Monitor sales declines, identify stores requiring attention and forecast future sales.")

    # Weekly comparison
    section_title("Weekly Sales Performance")
    comparison = weekly_comparison(filtered)

    if comparison["CurrentSales"] is not None:
        wow = comparison["WoW"]
        yoy = comparison["YoY"]
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            metric_card("Latest Weekly Sales", money(comparison["CurrentSales"]))
        with c2:
            metric_card("Previous Weekly Sales", money(comparison["PreviousSales"]))
        with c3:
            metric_card("Week-over-Week", f"{wow:+.2f}%" if pd.notna(wow) else "N/A")
        with c4:
            metric_card("Year-over-Year", f"{yoy:+.2f}%" if pd.notna(yoy) else "N/A")
    else:
        st.info("At least two weeks are required for sales comparisons.")

    st.divider()
    section_title("Automated Executive Findings")
    threshold = st.slider("Sales Decline Alert Threshold (%)", 5, 40, 10, 5)

    for finding in executive_findings(filtered, -threshold):
        insight_card("Business Observation", finding)

    # Store alerts
    st.divider()
    section_title("Store Performance Alerts")
    store_alerts = performance_alerts(filtered, -threshold)

    if store_alerts.empty:
        st.info("No comparable store-week records were found.")
    else:
        attention = store_alerts[store_alerts["Status"] == "Attention"].copy()
        attention["Severity"] = "Moderate"
        attention.loc[attention["ChangePct"] <= -20, "Severity"] = "High"
        attention.loc[attention["ChangePct"] <= -35, "Severity"] = "Critical"

        critical = int((attention["Severity"] == "Critical").sum())
        high = int((attention["Severity"] == "High").sum())
        moderate = int((attention["Severity"] == "Moderate").sum())

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("Stores Needing Review", f"{len(attention):,}")
        with c2:
            metric_card("Critical Declines", f"{critical:,}")
        with c3:
            metric_card("High Declines", f"{high:,}")
        with c4:
            metric_card("Combined Weekly Decline", money(attention["RevenueDecline"].sum()))

        if not attention.empty:
            chart_data = attention.sort_values("RevenueDecline", ascending=False).head(15).copy()
            chart_data["StoreLabel"] = "Store " + chart_data["Store"].astype(str)

            fig = px.bar(chart_data, x="RevenueDecline", y="StoreLabel", color="Severity", orientation="h", color_discrete_map={"Critical": "#DC2626", "High": "#F59E0B", "Moderate": "#2563EB"})
            fig.update_layout(xaxis_title="Sales Decline ($)", yaxis_title="Store", yaxis={"categoryorder": "total ascending"})
            show_chart(fig, "Stores Requiring Attention", 480)
        else:
            st.success("No stores exceeded the selected decline threshold.")

        section_title("Detailed Store Performance")
        st.dataframe(store_alerts.round(2), use_container_width=True, hide_index=True)

    # Department alerts
    st.divider()
    section_title("Department Performance Alerts")
    dept_alerts = department_alerts(filtered, -threshold)

    if dept_alerts.empty:
        st.success("No store-department combinations exceeded the decline threshold.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            metric_card("Store-Departments Needing Review", f"{len(dept_alerts):,}")
        with c2:
            metric_card("Combined Department Decline", money(dept_alerts["RevenueDecline"].sum()))

        dept_chart = dept_alerts.head(15).copy()
        dept_chart["DepartmentLabel"] = "Store " + dept_chart["Store"].astype(str) + " / Dept " + dept_chart["Dept"].astype(str)

        fig = px.bar(dept_chart, x="RevenueDecline", y="DepartmentLabel", orientation="h", color="ChangePct", color_continuous_scale="Reds_r")
        fig.update_layout(xaxis_title="Sales Decline ($)", yaxis_title="Store / Department", yaxis={"categoryorder": "total ascending"})
        show_chart(fig, "Largest Store-Department Declines", 520)

        section_title("Department Alert Details")
        st.dataframe(dept_alerts.head(50).round(2), use_container_width=True, hide_index=True)

    # Forecasting
    st.divider()
    section_title("Machine Learning Sales Forecasting")
    st.caption("Random Forest model evaluated against historical Walmart weekly sales.")

    c1, c2 = st.columns(2)
    with c1:
        test_weeks = st.slider("Historical Test Period (Weeks)", 8, 24, 20, 4)
    with c2:
        horizon = st.slider("Forecast Horizon (Weeks)", 1, 8, 4)

    current_scope = (tuple(sorted(selected_stores)), tuple(sorted(selected_types)), tuple(sorted(selected_depts)), str(start_date), str(end_date), test_weeks, horizon)

    if st.button("Train and Evaluate Forecast", type="primary"):
        with st.spinner("Training Random Forest forecasting model..."):
            try:
                metrics, evaluation, future = train_sales_forecast(filtered, test_weeks=test_weeks, horizon=horizon)
                st.session_state["forecast_results"] = (metrics, evaluation, future)
                st.session_state["forecast_scope"] = current_scope
                st.success("Forecast training completed successfully.")
            except Exception as error:
                st.session_state.pop("forecast_results", None)
                st.session_state.pop("forecast_scope", None)
                st.error(f"Forecasting failed: {error}")

    if "forecast_results" in st.session_state and st.session_state.get("forecast_scope") == current_scope:
        metrics, evaluation, future = st.session_state["forecast_results"]

        section_title("Forecast Model Accuracy")
        st.dataframe(metrics.round(2), use_container_width=True, hide_index=True)

        rf = metrics[metrics["Model"] == "Random Forest"]
        baseline = metrics[metrics["Model"] == "Last-week baseline"]

        if not rf.empty and not baseline.empty:
            rf_wape = float(rf.iloc[0]["WAPE"])
            baseline_wape = float(baseline.iloc[0]["WAPE"])

            c1, c2, c3 = st.columns(3)
            with c1:
                metric_card("Random Forest WAPE", f"{rf_wape:.2f}%")
            with c2:
                metric_card("Baseline WAPE", f"{baseline_wape:.2f}%")
            with c3:
                metric_card("WAPE Difference", f"{rf_wape - baseline_wape:+.2f} pp")

            if pd.notna(rf_wape) and pd.notna(baseline_wape):
                if rf_wape < baseline_wape:
                    insight_card("Forecast Evaluation", "Random Forest achieved a lower historical forecasting error than the baseline.", "success")
                elif rf_wape > baseline_wape:
                    insight_card("Forecast Evaluation", "The baseline performed better than Random Forest. The more complex model did not improve forecast accuracy.", "warning")
                else:
                    insight_card("Forecast Evaluation", "Both forecasting methods achieved the same historical WAPE.")

        st.divider()
        section_title("Historical Forecast Comparison")
        accuracy_chart = evaluation.melt(id_vars="Date", value_vars=["ActualSales", "PredictedSales", "BaselineSales"], var_name="Series", value_name="Sales")

        fig = px.line(accuracy_chart, x="Date", y="Sales", color="Series", color_discrete_map={"ActualSales": "#172B4D", "PredictedSales": "#0D9488", "BaselineSales": "#94A3B8"})
        fig.update_layout(xaxis_title="Week", yaxis_title="Weekly Sales ($)")
        show_chart(fig, "Actual vs Predicted Weekly Sales", 470)

        st.divider()
        section_title("Future Weekly Sales Forecast")
        fig = px.line(future, x="Date", y="PredictedSales", markers=True, color_discrete_sequence=["#0D9488"])
        fig.update_traces(line=dict(width=3, dash="dash"), marker=dict(size=9))
        fig.update_layout(xaxis_title="Forecast Week", yaxis_title="Projected Weekly Sales ($)")
        show_chart(fig, "Projected Weekly Sales", 430)

        st.dataframe(future.round(2), use_container_width=True, hide_index=True)
        st.caption("Forecasts are historical demonstrations based on 2010–2012 data. Point estimates are not guaranteed outcomes.")

        forecast_csv = future.to_csv(index=False).encode("utf-8")
        st.download_button("Download Forecast CSV", data=forecast_csv, file_name="salesmind_forecast.csv", mime="text/csv")

# Application footer
st.divider()
st.caption("SalesMind AI | Walmart Store Sales Forecasting Dataset | Historical data: 2010–2012 | Currency: USD")
st.caption("Recorded sales are not profit. All charts and KPIs reflect the selected filters.")
# TAB 7 - Management Reports
with tabs[7]:
    section_title("Management Reports")
    st.caption("Generate weekly and monthly PDF reports using the selected Walmart sales data.")
    st.info("Reports use your current dashboard filters: stores, store types, departments and dates.")

    c1, c2 = st.columns(2)
    with c1:
        report_type = st.selectbox("Report Type", ["Weekly", "Monthly"], key="report_type")
    with c2:
        report_threshold = st.slider("Store Decline Alert Threshold (%)", 5, 40, 10, 5, key="report_threshold")

    if report_type == "Weekly":
        available_periods = sorted(filtered["Date"].dropna().unique(), reverse=True)
        period = st.selectbox("Reporting Week", available_periods, format_func=lambda d: pd.Timestamp(d).strftime("%d %B %Y"), key="weekly_report_period")
    else:
        available_periods = sorted(filtered["Date"].dt.to_period("M").unique(), reverse=True)
        period = st.selectbox("Reporting Month", available_periods, format_func=lambda p: p.strftime("%B %Y"), key="monthly_report_period")

    if not available_periods:
        st.warning("No reporting periods are available.")
        st.stop()

    period_label = pd.Timestamp(period).strftime("%d %B %Y") if report_type == "Weekly" else period.strftime("%B %Y")
    report_current = filtered[filtered["Date"] == pd.Timestamp(period)] if report_type == "Weekly" else filtered[filtered["Date"].dt.to_period("M") == period]
    report_sales = float(report_current["Weekly_Sales"].sum())

    st.divider()
    section_title("Report Preview")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Reporting Period Sales", money(report_sales))
    with c2:
        metric_card("Active Stores", f"{report_current['Store'].nunique():,}")
    with c3:
        metric_card("Departments", f"{report_current['Dept'].nunique():,}")
    with c4:
        metric_card("Observed Weeks", f"{report_current['Date'].nunique():,}")

    st.caption(f"Selected reporting period: {period_label}")
    st.caption("Monthly reporting assigns each weekly sales observation to the calendar month of its week date.")

    st.divider()
    section_title("Report Contents")
    st.markdown("**Executive summary** — sales, period comparisons and KPI calculations")
    st.markdown("**Sales analysis** — historical sales trend and supporting chart")
    st.markdown("**Store rankings** — highest-sales stores and average weekly performance")
    st.markdown("**Department performance** — highest-revenue departments")
    st.markdown("**Performance alerts** — stores with significant recorded sales declines")
    st.markdown("**Reporting context** — holiday observations and data limitations")

    include_forecast = st.checkbox("Include latest valid forecast results, if available", value=False, key="report_include_forecast")
    forecast_metrics = None
    forecast_future = None

    if include_forecast:
        if "forecast_results" in st.session_state:
            saved_scope = st.session_state.get("forecast_scope")
            if saved_scope is not None:
                scope_matches = saved_scope[:5] == (tuple(sorted(selected_stores)), tuple(sorted(selected_types)), tuple(sorted(selected_depts)), str(start_date), str(end_date))
                if scope_matches:
                    forecast_metrics, _, forecast_future = st.session_state["forecast_results"]
                    st.success("Matching forecast results found.")
                else:
                    st.warning("The stored forecast uses different dashboard filters. It will not be included.")
            else:
                st.warning("Forecast scope information is missing. The forecast will not be included.")
        else:
            st.info("No forecast has been trained. Use the Performance Intelligence tab first.")

    st.divider()

    if st.button("Generate Management Report", type="primary", key="generate_pdf"):
        with st.spinner("Creating your management PDF report..."):
            try:
                pdf_data = generate_management_report(filtered, report_type, period, threshold=-report_threshold, forecast_metrics=forecast_metrics, forecast_future=forecast_future)
                st.session_state["report_pdf"] = pdf_data
                st.session_state["report_name"] = f"SalesMind_{report_type}_{pd.Timestamp(period):%Y_%m_%d}.pdf"
                st.session_state["report_signature"] = (report_type, str(period), report_threshold, tuple(sorted(selected_stores)), tuple(sorted(selected_types)), tuple(sorted(selected_depts)), str(start_date), str(end_date), bool(forecast_metrics is not None))
                st.success("Management report generated successfully.")
            except Exception as error:
                st.session_state.pop("report_pdf", None)
                st.error(f"Report generation failed: {error}")

    report_signature = (report_type, str(period), report_threshold, tuple(sorted(selected_stores)), tuple(sorted(selected_types)), tuple(sorted(selected_depts)), str(start_date), str(end_date), bool(forecast_metrics is not None))

    if "report_pdf" in st.session_state and st.session_state.get("report_signature") == report_signature:
        st.download_button("Download Management Report (PDF)", data=st.session_state["report_pdf"], file_name=st.session_state["report_name"], mime="application/pdf", type="primary")
        st.caption("The PDF contains the values calculated when Generate Management Report was clicked.")

    st.divider()
    st.caption("SalesMind AI | Management Reporting | Historical Walmart dataset (2010–2012)")

# TAB 8 - System Health
# TAB 8 - System Health
with tabs[8]:
    section_title("System Health & Data Reliability")
    st.caption("Validate Walmart data integrity, reporting consistency, store coverage and forecasting accuracy.")

    # Dataset validation
    section_title("Dataset Health")
    raw_checks = validate_raw_data(train, features, stores)
    clean_checks = validate_clean_data(df)
    full_coverage = store_week_coverage(df)
    selected_coverage = store_week_coverage(filtered)
    summary = health_summary(raw_checks, clean_checks, full_coverage)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Passed Checks", f"{summary['Passed']:,}")
    with c2:
        metric_card("Warnings", f"{summary['Warnings']:,}")
    with c3:
        metric_card("Failed Checks", f"{summary['Failures']:,}")
    with c4:
        metric_card("Missing Store-Weeks", f"{summary['MissingStoreWeeks']:,}")

    if summary["Health"] == "Critical":
        st.error("Critical validation issues were detected. Review failed checks before relying on the data.")
    elif summary["Health"] == "Review":
        st.warning("The dataset passed critical checks, but some warnings need review.")
    else:
        st.success("No issues were detected by the configured dataset checks.")

    st.divider()
    section_title("Raw Data Validation")
    st.dataframe(raw_checks, use_container_width=True, hide_index=True)

    section_title("Cleaned Data Validation")
    st.dataframe(clean_checks, use_container_width=True, hide_index=True)

    # Store-week coverage
    st.divider()
    section_title("Store-Week Coverage")
    st.caption("Coverage is measured across the observed reporting dates. Filtered department selections can reduce apparent coverage.")

    coverage_mode = st.radio("Coverage Dataset", ["Full Cleaned Dataset", "Current Dashboard Selection"], horizontal=True, key="coverage_mode")
    coverage = full_coverage if coverage_mode == "Full Cleaned Dataset" else selected_coverage

    if not coverage.empty:
        c1, c2, c3 = st.columns(3)
        with c1:
            metric_card("Stores Evaluated", f"{len(coverage):,}")
        with c2:
            metric_card("Average Coverage", f"{coverage['CoveragePct'].mean():.2f}%")
        with c3:
            metric_card("Missing Store-Weeks", f"{coverage['MissingWeeks'].sum():,}")

        coverage_chart = coverage.copy()
        coverage_chart["StoreLabel"] = "Store " + coverage_chart["Store"].astype(str)
        fig = px.bar(coverage_chart, x="StoreLabel", y="CoveragePct", color="CoveragePct", color_continuous_scale="RdYlGn", range_color=[0, 100])
        fig.update_layout(xaxis_title="Store", yaxis_title="Observed Week Coverage (%)", xaxis_tickangle=-45)
        show_chart(fig, "Store Weekly Coverage", 450)

        st.dataframe(coverage.round(2), use_container_width=True, hide_index=True)
    else:
        st.warning("Store coverage cannot be calculated for the current selection.")

    # Dashboard and PDF reconciliation
    st.divider()
    section_title("Dashboard & PDF KPI Reconciliation")
    st.caption("Compare dashboard KPI functions with the same calculations used by the PDF report generator.")

    health_report_type = st.selectbox("Reporting Period Type", ["Weekly", "Monthly"], key="health_report_type")

    if health_report_type == "Weekly":
        health_periods = sorted(filtered["Date"].dropna().unique(), reverse=True)
        health_period = st.selectbox("Select Week", health_periods, format_func=lambda d: pd.Timestamp(d).strftime("%d %B %Y"), key="health_week")
    else:
        health_periods = sorted(filtered["Date"].dt.to_period("M").unique(), reverse=True)
        health_period = st.selectbox("Select Month", health_periods, format_func=lambda p: p.strftime("%B %Y"), key="health_month")

    if health_periods:
        reconciliation = reconcile_report_kpis(filtered, health_report_type, health_period)
        period_coverage = reporting_period_coverage(filtered, health_report_type, health_period)
        failed_metrics = int((reconciliation["Status"] == "FAIL").sum())

        c1, c2, c3 = st.columns(3)
        with c1:
            metric_card("Reconciled Metrics", f"{len(reconciliation) - failed_metrics:,}/{len(reconciliation)}")
        with c2:
            metric_card("Metric Mismatches", f"{failed_metrics:,}")
        with c3:
            metric_card("Observed Report Weeks", f"{period_coverage['ObservedWeeks']:,}")

        if failed_metrics == 0:
            st.success("Dashboard and PDF calculation functions agree for the selected reporting period.")
        else:
            st.error("Dashboard and PDF calculations contain mismatches.")

        if not period_coverage["PreviousPeriodAvailable"]:
            st.warning("No previous reporting period is available within the current selection.")

        st.dataframe(reconciliation.round(3), use_container_width=True, hide_index=True)
        st.caption("This reconciles reporting calculations, not the rendered PDF text or visual layout.")

    # Automated forecasting backtesting
    st.divider()
    section_title("Forecast Model Backtesting")
    st.caption("Expanding-window evaluation on continuous historical weekly sales. Results depend on the currently selected stores, departments and dates.")

    c1, c2 = st.columns(2)
    with c1:
        n_splits = st.slider("Number of Backtesting Folds", min_value=2, max_value=5, value=3, key="bt_splits")
    with c2:
        test_weeks = st.slider("Test Weeks per Fold", min_value=4, max_value=12, value=8, step=2, key="bt_test_weeks")

    min_train_weeks = 70
    required_weeks = min_train_weeks + n_splits * test_weeks
    available_weeks = filtered["Date"].nunique()

    st.caption(f"Available reporting weeks: {available_weeks} | Minimum required: {required_weeks}")

    backtest_scope = (tuple(sorted(selected_stores)), tuple(sorted(selected_types)), tuple(sorted(selected_depts)), str(start_date), str(end_date), n_splits, test_weeks)

    if st.button("Run Forecast Backtesting", type="primary", key="run_backtesting"):
        with st.spinner("Evaluating Random Forest and forecasting baselines..."):
            try:
                results, predictions = backtest_sales(filtered, n_splits=n_splits, test_weeks=test_weeks, min_train_weeks=min_train_weeks)
                summary_results = summarize_backtesting(results, predictions)
                st.session_state["backtest_results"] = (results, predictions, summary_results)
                st.session_state["backtest_scope"] = backtest_scope
                st.success("Backtesting completed successfully.")
            except Exception as error:
                st.session_state.pop("backtest_results", None)
                st.session_state.pop("backtest_scope", None)
                st.error(f"Backtesting failed: {error}")

    if "backtest_results" in st.session_state and st.session_state.get("backtest_scope") == backtest_scope:
        results, predictions, summary_results = st.session_state["backtest_results"]

        section_title("Backtesting Model Comparison")
        st.dataframe(summary_results.round(2), use_container_width=True, hide_index=True)

        best_model = summary_results.iloc[0]
        c1, c2, c3 = st.columns(3)
        with c1:
            metric_card("Lowest-WAPE Model", str(best_model["Model"]))
        with c2:
            metric_card("Best WAPE", f"{best_model['WAPE']:.2f}%")
        with c3:
            metric_card("Evaluation Folds", f"{int(best_model['Folds']):,}")

        fig = px.bar(summary_results, x="Model", y="WAPE", color="Model", color_discrete_sequence=["#0D9488", "#2563EB", "#8B5CF6"])
        fig.update_layout(xaxis_title="Model", yaxis_title="Weighted Absolute Percentage Error (%)", showlegend=False)
        show_chart(fig, "Forecast Accuracy Comparison", 430)

        section_title("Forecast Error by Backtesting Fold")
        fig = px.line(results, x="Fold", y="WAPE", color="Model", markers=True, color_discrete_sequence=["#0D9488", "#2563EB", "#8B5CF6"])
        fig.update_layout(xaxis_title="Backtesting Fold", yaxis_title="WAPE (%)")
        show_chart(fig, "Historical Model Consistency", 420)

        section_title("Actual vs Predicted Sales")
        fig = px.line(predictions, x="Date", y="PredictedSales", color="Model", color_discrete_sequence=["#0D9488", "#2563EB", "#8B5CF6"])
        actual = predictions[predictions["Model"] == "Random Forest"]
        fig.add_scatter(x=actual["Date"], y=actual["ActualSales"], mode="lines", name="Actual Sales", line=dict(color="#172B4D", width=3))
        fig.update_layout(xaxis_title="Week", yaxis_title="Weekly Sales ($)")
        show_chart(fig, "Backtested Sales Forecasts", 470)

        section_title("Detailed Backtesting Results")
        st.dataframe(results.round(2), use_container_width=True, hide_index=True)

        backtest_csv = results.to_csv(index=False).encode("utf-8")
        st.download_button("Download Backtesting Results CSV", data=backtest_csv, file_name="salesmind_backtesting.csv", mime="text/csv")

        st.caption("Backtesting accuracy is historical evidence, not a guarantee of future forecast performance.")

    st.divider()
    st.caption("System Health evaluates data integrity, calculation consistency and historical forecasting. It is not a security audit or a production deployment certification.")


# TAB 9 - Multi-Business Workspace
with tabs[9]:
    render_business_workspace()