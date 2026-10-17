import numpy as np
import pandas as pd
from modules.analytics import calculate_kpis
from modules.report_generator import prepare_period, calculate_report_metrics

KEYS = ["Store", "Dept", "Date"]
REQUIRED = ["Store", "Dept", "Date", "Weekly_Sales", "IsHoliday"]

def check_result(name, status, details, value=None):
    return {"Check": name, "Status": status, "Details": details, "Value": value}

def validate_raw_data(train, features, stores):
    checks = []
    for name, frame, required in [
        ("Sales", train, REQUIRED),
        ("Features", features, ["Store", "Date", "IsHoliday"]),
        ("Stores", stores, ["Store", "Type", "Size"])
    ]:
        missing = sorted(set(required) - set(frame.columns))
        checks.append(check_result(f"{name} schema", "FAIL" if missing else "PASS", f"Missing columns: {missing}" if missing else "Required columns present", len(missing)))
        checks.append(check_result(f"{name} records", "FAIL" if frame.empty else "PASS", f"{len(frame):,} rows", len(frame)))

    if all(c in train.columns for c in KEYS):
        count = int(train.duplicated(KEYS).sum())
        checks.append(check_result("Duplicate sales keys", "FAIL" if count else "PASS", "Repeated Store-Dept-Date keys", count))
        null_keys = int(train[KEYS].isna().any(axis=1).sum())
        checks.append(check_result("Missing sales keys", "FAIL" if null_keys else "PASS", "Rows with missing store, department or date", null_keys))

    if all(c in features.columns for c in ["Store", "Date"]):
        count = int(features.duplicated(["Store", "Date"]).sum())
        checks.append(check_result("Duplicate feature keys", "FAIL" if count else "PASS", "Repeated Store-Date feature keys", count))

    if "Store" in stores.columns:
        count = int(stores.duplicated("Store").sum())
        checks.append(check_result("Duplicate store keys", "FAIL" if count else "PASS", "Repeated store identifiers", count))

    if "Weekly_Sales" in train.columns:
        sales = pd.to_numeric(train["Weekly_Sales"], errors="coerce")
        invalid = int(sales.isna().sum() + np.isinf(sales.dropna()).sum())
        negatives = int((sales < 0).sum())
        checks.append(check_result("Invalid sales values", "FAIL" if invalid else "PASS", "Missing, nonnumeric or infinite weekly sales", invalid))
        checks.append(check_result("Negative sales values", "WARN" if negatives else "PASS", "Negative sales retained as recorded adjustments", negatives))

    for column in ["MarkDown1", "MarkDown2", "MarkDown3", "MarkDown4", "MarkDown5"]:
        if column in features.columns:
            count = int(features[column].isna().sum())
            checks.append(check_result(f"{column} missing values", "WARN" if count else "PASS", "Historical promotional data availability", count))

    return pd.DataFrame(checks)

def validate_clean_data(df):
    checks = []
    missing = sorted(set(REQUIRED) - set(df.columns))
    if missing:
        return pd.DataFrame([check_result("Cleaned schema", "FAIL", f"Missing columns: {missing}", len(missing))])
    checks.append(check_result("Cleaned records", "FAIL" if df.empty else "PASS", f"{len(df):,} rows", len(df)))
    if df.empty:
        return pd.DataFrame(checks)

    keys = int(df[KEYS].isna().any(axis=1).sum())
    duplicates = int(df.duplicated(KEYS).sum())
    sales = pd.to_numeric(df["Weekly_Sales"], errors="coerce")
    invalid = int(sales.isna().sum() + np.isinf(sales.dropna()).sum())
    checks.append(check_result("Required identifiers", "FAIL" if keys else "PASS", "Missing store, department or date", keys))
    checks.append(check_result("Unique sales keys", "FAIL" if duplicates else "PASS", "Duplicate Store-Dept-Date combinations", duplicates))
    checks.append(check_result("Sales numeric integrity", "FAIL" if invalid else "PASS", "Missing or infinite sales", invalid))

    dates = pd.to_datetime(df["Date"], errors="coerce")
    invalid_dates = int(dates.isna().sum())
    checks.append(check_result("Valid dates", "FAIL" if invalid_dates else "PASS", "Invalid reporting dates", invalid_dates))

    negative = int((sales < 0).sum())
    checks.append(check_result("Negative sales adjustments", "WARN" if negative else "PASS", "Negative sales records preserved", negative))
    if "Type" in df.columns:
        unknown = int(df["Type"].isna().sum())
        checks.append(check_result("Store metadata coverage", "FAIL" if unknown else "PASS", "Rows without store type", unknown))
    return pd.DataFrame(checks)

def store_week_coverage(df):
    columns = ["Store", "ObservedWeeks", "ExpectedWeeks", "MissingWeeks", "CoveragePct", "FirstWeek", "LastWeek"]
    if df.empty or not {"Store", "Date"}.issubset(df.columns):
        return pd.DataFrame(columns=columns)
    dates = pd.to_datetime(df["Date"]).dropna().drop_duplicates().sort_values()
    expected = pd.date_range(dates.min(), dates.max(), freq="7D")
    if len(expected) != len(dates) or not dates.reset_index(drop=True).equals(pd.Series(expected)):
        expected = pd.date_range(dates.min(), dates.max(), freq="7D")
    result = []
    for store, group in df.groupby("Store"):
        observed_dates = pd.DatetimeIndex(pd.to_datetime(group["Date"]).dropna().unique())
        observed = len(observed_dates)
        missing = len(expected.difference(observed_dates))
        result.append({"Store": store, "ObservedWeeks": observed, "ExpectedWeeks": len(expected), "MissingWeeks": missing, "CoveragePct": observed / len(expected) * 100 if len(expected) else 0, "FirstWeek": observed_dates.min() if observed else pd.NaT, "LastWeek": observed_dates.max() if observed else pd.NaT})
    return pd.DataFrame(result).sort_values(["CoveragePct", "Store"]).reset_index(drop=True)

def reporting_period_coverage(df, report_type, period):
    data, current, previous, label, previous_label = prepare_period(df, report_type, period)
    dates = pd.DatetimeIndex(sorted(current["Date"].drop_duplicates()))
    all_dates = pd.DatetimeIndex(sorted(data["Date"].drop_duplicates()))
    if report_type == "Weekly":
        expected = 1
        valid = len(dates) == expected
    else:
        month = pd.Period(period, freq="M")
        expected_dates = all_dates[all_dates.to_period("M") == month]
        expected = len(expected_dates)
        valid = len(dates) == expected and expected > 0
    return {"Period": label, "ObservedWeeks": len(dates), "ExpectedWeeksInSelection": expected, "CompleteWithinSelection": valid, "PreviousPeriodAvailable": not previous.empty}

def reconcile_report_kpis(df, report_type, period, tolerance=0.01):
    data, current, previous, label, previous_label = prepare_period(df, report_type, period)
    dashboard = calculate_kpis(current)
    report = calculate_report_metrics(current, previous)
    comparisons = [
        ("Recorded sales", dashboard["Total Sales"], report["sales"]),
        ("Active stores", dashboard["Stores"], report["stores"]),
        ("Departments", dashboard["Departments"], report["departments"]),
        ("Observed weeks", dashboard["Weeks"], report["weeks"]),
        ("Average store-week sales", dashboard["Average Store-Week Sales"], report["average_store_week"]),
        ("Negative sales records", dashboard["Negative Sales Rows"], report["negative_rows"])
    ]
    results = []
    for name, left, right in comparisons:
        difference = abs(float(left) - float(right))
        results.append({"Metric": name, "Dashboard": float(left), "PDFCalculation": float(right), "Difference": difference, "Status": "PASS" if difference <= tolerance else "FAIL"})
    return pd.DataFrame(results)

def health_summary(raw_checks, clean_checks, coverage, reconciliation=None):
    frames = [raw_checks, clean_checks]
    statuses = pd.concat(frames, ignore_index=True)["Status"].value_counts()
    failures = int(statuses.get("FAIL", 0))
    warnings = int(statuses.get("WARN", 0))
    passing = int(statuses.get("PASS", 0))
    missing_store_weeks = int(coverage["MissingWeeks"].sum()) if not coverage.empty else 0
    if missing_store_weeks:
        warnings += 1
    if reconciliation is not None and not reconciliation.empty:
        failures += int((reconciliation["Status"] == "FAIL").sum())
        passing += int((reconciliation["Status"] == "PASS").sum())
    return {"Passed": passing, "Warnings": warnings, "Failures": failures, "MissingStoreWeeks": missing_store_weeks, "Health": "Critical" if failures else "Review" if warnings else "Healthy"}