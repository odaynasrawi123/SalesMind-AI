import pandas as pd
import pytest
from modules.business_loader import suggest_mapping, validate_mapping, normalize_business_data
from modules.business_analytics import business_kpis, business_breakdown, business_customer_analysis

@pytest.fixture
def business_data():
    return pd.DataFrame({
        "OrderDate": ["2026-09-01", "2026-09-02", "2026-09-03"],
        "OrderID": ["A1", "A2", "A3"],
        "Quantity": [2, 3, 1],
        "UnitPrice": [100, 50, 200],
        "CustomerID": ["C1", "C2", "C1"],
        "Category": ["Electronics", "Furniture", "Electronics"]
    })

def test_column_suggestions(business_data):
    mapping = suggest_mapping(business_data.columns)
    assert mapping["Date"] == "OrderDate"
    assert mapping["Quantity"] == "Quantity"
    assert mapping["UnitPrice"] == "UnitPrice"

def test_calculated_revenue(business_data):
    mapping = suggest_mapping(business_data.columns)
    cleaned, quality = normalize_business_data(business_data, mapping)
    assert cleaned["Revenue"].sum() == 550
    assert quality["ExcludedRows"] == 0

def test_business_kpis(business_data):
    cleaned, _ = normalize_business_data(business_data, suggest_mapping(business_data.columns))
    kpis = business_kpis(cleaned)
    assert kpis["Orders"] == 3
    assert kpis["Customers"] == 2
    assert kpis["NetRecordedSales"] == 550

def test_category_breakdown(business_data):
    cleaned, _ = normalize_business_data(business_data, suggest_mapping(business_data.columns))
    result = business_breakdown(cleaned, "Category")
    assert result["Sales"].sum() == 550

def test_customer_analysis(business_data):
    cleaned, _ = normalize_business_data(business_data, suggest_mapping(business_data.columns))
    customers = business_customer_analysis(cleaned)
    assert customers.loc[customers["CustomerID"] == "C1", "Orders"].iloc[0] == 2

def test_invalid_date_excluded(business_data):
    data = business_data.copy()
    data.loc[0, "OrderDate"] = "invalid"
    cleaned, quality = normalize_business_data(data, suggest_mapping(data.columns))
    assert len(cleaned) == 2
    assert quality["InvalidDates"] == 1

def test_duplicate_column_mapping_rejected():
    with pytest.raises(ValueError):
        validate_mapping({"Date": "Column1", "Revenue": "Column1"})