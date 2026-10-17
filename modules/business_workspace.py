import streamlit as st
import plotly.express as px
import pandas as pd
from modules.business_loader import FIELDS, read_business_file, suggest_mapping, normalize_business_data
from modules.business_analytics import business_kpis, business_trend, business_breakdown, business_customer_analysis, business_monthly_growth, business_findings
from modules.ui import section_title, metric_card, show_chart, insight_card

def render_business_workspace():
    section_title("Your Business Workspace")
    st.caption("Upload a sales file, map its columns and explore business performance.")
    st.warning("Phase 7 is a local single-session prototype. Do not upload sensitive customer data to a public deployment.")

    uploaded = st.file_uploader("Upload Business Sales File", type=["csv", "xlsx"], key="business_upload")
    if uploaded is None:
        st.info("Upload a CSV or Excel file to begin.")
        return

    try:
        raw = read_business_file(uploaded)
    except Exception as error:
        st.error(f"File loading failed: {error}")
        return

    if raw.empty:
        st.warning("The uploaded file contains no rows.")
        return
    if raw.columns.duplicated().any():
        st.error("The uploaded file contains duplicate column names. Rename them before continuing.")
        return

    section_title("1. File Preview")
    c1, c2 = st.columns(2)
    c1.metric("Rows", f"{len(raw):,}")
    c2.metric("Columns", f"{len(raw.columns):,}")
    st.dataframe(raw.head(15), use_container_width=True, hide_index=True)

    section_title("2. Map Your Columns")
    suggested = suggest_mapping(raw.columns)
    options = ["Not available"] + raw.columns.astype(str).tolist()
    mapping = {}
    c1, c2 = st.columns(2)
    for index, field in enumerate(FIELDS):
        default = str(suggested[field]) if suggested[field] is not None else "Not available"
        with (c1 if index % 2 == 0 else c2):
            choice = st.selectbox(field, options, index=options.index(default) if default in options else 0, key=f"mapping_{field}")
            mapping[field] = None if choice == "Not available" else choice

    dayfirst = st.checkbox("Dates use day/month/year format", value=False)
    currency = st.text_input("Currency label", value="USD", max_chars=12)
    st.caption("Use one currency per file. This setting changes display labels only; it does not convert currencies.")

    if not st.button("Validate & Analyze", type="primary", key="business_analyze"):
        return

    try:
        data, quality = normalize_business_data(raw, mapping, dayfirst)
    except Exception as error:
        st.error(f"Validation failed: {error}")
        return

    if data.empty:
        st.error("No valid records remain after cleaning.")
        return

    section_title("3. Data Quality")
    c1, c2, c3 = st.columns(3)
    c1.metric("Original Rows", f"{quality['OriginalRows']:,}")
    c2.metric("Valid Rows", f"{quality['ValidRows']:,}")
    c3.metric("Excluded Rows", f"{quality['ExcludedRows']:,}")
    if quality["ExcludedRows"]:
        st.warning(f"{quality['ExcludedRows']:,} records were excluded because of invalid dates or revenue.")

    section_title("4. Executive Dashboard")
    kpis = business_kpis(data)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Net Recorded Sales", f"{currency} {kpis['NetRecordedSales']:,.2f}")
    c2.metric("Positive Sales", f"{currency} {kpis['PositiveSales']:,.2f}")
    c3.metric("Negative Adjustments", f"{currency} {kpis['NegativeAdjustments']:,.2f}")
    c4.metric("Records", f"{kpis['Transactions']:,}")

    optional = [("Orders", "Orders"), ("Customers", "Customers"), ("Products", "Products"), ("Stores", "Stores"), ("Units", "Units"), ("AOV", "Average Positive Order Value")]
    available = [(title, key) for key, title in optional if kpis[key] is not None]
    if available:
        cols = st.columns(min(4, len(available)))
        for index, (label, key) in enumerate(available):
            value = kpis[key]
            display = f"{currency} {value:,.2f}" if key == "AOV" else f"{value:,.0f}"
            cols[index % len(cols)].metric(label, display)

    section_title("Sales Trends")
    frequency = st.selectbox("Time Grouping", ["Daily", "Weekly", "Monthly"], index=2, key="business_frequency")
    freq = {"Daily": "D", "Weekly": "W-FRI", "Monthly": "MS"}[frequency]
    trend = business_trend(data, freq)
    fig = px.line(trend, x="Date", y="Sales", markers=True)
    fig.update_layout(yaxis_title=f"Sales ({currency})", xaxis_title="")
    show_chart(fig, f"{frequency} Sales Performance", 430)

    section_title("Sales Breakdown")
    available_dimensions = [field for field in ["Store", "Category", "Product", "Country"] if field in data]
    if available_dimensions:
        dimension = st.selectbox("Analyze By", available_dimensions, key="business_dimension")
        breakdown = business_breakdown(data, dimension)
        fig = px.bar(breakdown, x="Sales", y=dimension, orientation="h")
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, xaxis_title=f"Sales ({currency})")
        show_chart(fig, f"Sales by {dimension}", 470)
        st.dataframe(breakdown, use_container_width=True, hide_index=True)
    else:
        st.info("Map a store, category, product or country column to enable breakdown charts.")

    if "CustomerID" in data:
        section_title("Customer Performance")
        customers = business_customer_analysis(data)
        st.dataframe(customers.head(20), use_container_width=True, hide_index=True)
        if "Orders" in customers:
            repeat = int((customers["Orders"] >= 2).sum())
            st.metric("Customers With 2+ Orders", f"{repeat:,}")

    section_title("Automated Business Findings")
    for finding in business_findings(data):
        insight_card("Business Observation", f"{finding} Currency: {currency}.")

    section_title("Export Cleaned Data")
    st.download_button("Download Cleaned CSV", data=data.to_csv(index=False).encode("utf-8"), file_name="salesmind_business_cleaned.csv", mime="text/csv")