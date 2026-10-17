import io
from pypdf import PdfReader
from modules.data_validation import reconcile_report_kpis
from modules.report_generator import prepare_period, calculate_report_metrics, generate_management_report

def test_weekly_report_reconciliation(sample_walmart):
    period = sample_walmart["Date"].max()
    result = reconcile_report_kpis(sample_walmart, "Weekly", period)
    assert (result["Status"] == "PASS").all()

def test_monthly_report_reconciliation(sample_walmart):
    period = sample_walmart["Date"].max().to_period("M")
    result = reconcile_report_kpis(sample_walmart, "Monthly", period)
    assert (result["Status"] == "PASS").all()

def test_weekly_period_selection(sample_walmart):
    period = sample_walmart["Date"].max()
    data, current, previous, label, previous_label = prepare_period(sample_walmart, "Weekly", period)
    assert current["Date"].nunique() == 1
    assert current["Date"].iloc[0] == period
    assert previous["Date"].nunique() == 1

def test_monthly_period_selection(sample_walmart):
    period = sample_walmart["Date"].max().to_period("M")
    data, current, previous, label, previous_label = prepare_period(sample_walmart, "Monthly", period)
    assert current["Date"].dt.to_period("M").eq(period).all()
    assert previous["Date"].dt.to_period("M").eq(period - 1).all()

def test_report_sales_match_source(sample_walmart):
    period = sample_walmart["Date"].max()
    data, current, previous, label, previous_label = prepare_period(sample_walmart, "Weekly", period)
    metrics = calculate_report_metrics(current, previous)
    assert abs(metrics["sales"] - current["Weekly_Sales"].sum()) < 0.01

def test_generated_pdf(sample_walmart):
    period = sample_walmart["Date"].max()
    pdf = generate_management_report(sample_walmart, "Weekly", period)
    assert pdf.startswith(b"%PDF")
    reader = PdfReader(io.BytesIO(pdf))
    assert len(reader.pages) >= 1
    text = " ".join(page.extract_text() or "" for page in reader.pages)
    assert "SalesMind AI" in text
    assert "Executive Summary" in text