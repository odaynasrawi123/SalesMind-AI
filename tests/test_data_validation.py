import pandas as pd
from modules.data_validation import validate_raw_data, validate_clean_data, store_week_coverage, health_summary

def test_valid_raw_data(raw_walmart):
    train, features, stores = raw_walmart
    results = validate_raw_data(train, features, stores)
    assert not (results["Status"] == "FAIL").any()

def test_duplicate_sales_keys_detected(raw_walmart):
    train, features, stores = raw_walmart
    train = pd.concat([train, train.iloc[[0]]], ignore_index=True)
    results = validate_raw_data(train, features, stores)
    check = results[results["Check"] == "Duplicate sales keys"].iloc[0]
    assert check["Status"] == "FAIL"
    assert check["Value"] == 1

def test_clean_data_integrity(sample_walmart):
    results = validate_clean_data(sample_walmart)
    assert not (results["Status"] == "FAIL").any()

def test_missing_store_week_detected(sample_walmart):
    missing_date = sample_walmart["Date"].min() + pd.Timedelta(weeks=3)
    data = sample_walmart[~((sample_walmart["Store"] == 1) & (sample_walmart["Date"] == missing_date))]
    coverage = store_week_coverage(data)
    store = coverage[coverage["Store"] == 1].iloc[0]
    assert store["MissingWeeks"] == 1
    assert store["CoveragePct"] < 100

def test_missing_metadata_detected(sample_walmart):
    data = sample_walmart.copy()
    data.loc[0, "Type"] = None
    checks = validate_clean_data(data)
    result = checks[checks["Check"] == "Store metadata coverage"].iloc[0]
    assert result["Status"] == "FAIL"

def test_health_summary_reports_failure(raw_walmart, sample_walmart):
    train, features, stores = raw_walmart
    train = pd.concat([train, train.iloc[[0]]], ignore_index=True)
    raw = validate_raw_data(train, features, stores)
    cleaned = validate_clean_data(sample_walmart)
    coverage = store_week_coverage(sample_walmart)
    summary = health_summary(raw, cleaned, coverage)
    assert summary["Failures"] >= 1
    assert summary["Health"] == "Critical"