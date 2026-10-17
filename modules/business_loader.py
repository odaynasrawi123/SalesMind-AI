from io import BytesIO
import pandas as pd

FIELDS = {
    "Date": ["date", "order_date", "invoice_date", "transaction_date", "sales_date"],
    "Revenue": ["revenue", "sales", "total", "sales_amount", "total_amount", "amount"],
    "Quantity": ["quantity", "qty", "units", "units_sold"],
    "UnitPrice": ["unit_price", "unitprice", "price", "selling_price"],
    "OrderID": ["order_id", "orderid", "invoice_no", "invoiceno", "invoice", "transaction_id"],
    "Product": ["product", "product_name", "item", "description", "item_name"],
    "Category": ["category", "product_category", "department"],
    "CustomerID": ["customer_id", "customerid", "client_id", "buyer_id"],
    "Store": ["store", "store_id", "branch", "location"],
    "Country": ["country", "region", "market"]
}

def read_business_file(uploaded_file):
    name = uploaded_file.name.lower()
    content = BytesIO(uploaded_file.getvalue())
    if name.endswith(".csv"):
        try:
            return pd.read_csv(content, encoding="utf-8-sig")
        except UnicodeDecodeError:
            content.seek(0)
            return pd.read_csv(content, encoding="cp1252")
    if name.endswith(".xlsx"):
        return pd.read_excel(content, engine="openpyxl")
    raise ValueError("Upload a CSV or XLSX file.")

def suggest_mapping(columns):
    def normalize(name):
        return "".join(char.lower() for char in str(name) if char.isalnum())

    normalized = {normalize(col): col for col in columns}
    result = {}

    for field, aliases in FIELDS.items():
        candidates = [field] + aliases
        result[field] = next((normalized[normalize(name)] for name in candidates if normalize(name) in normalized), None)

    return result

def validate_mapping(mapping):
    selected = [value for value in mapping.values() if value is not None]
    if len(selected) != len(set(selected)):
        raise ValueError("A source column cannot be assigned to multiple fields.")
    if mapping.get("Date") is None:
        raise ValueError("Map a date column.")
    if mapping.get("Revenue") is None and not (mapping.get("Quantity") and mapping.get("UnitPrice")):
        raise ValueError("Map Revenue or both Quantity and UnitPrice.")

def parse_amount(series):
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    text = series.astype("string").str.strip().str.replace(r"[$£€,\s]", "", regex=True)
    return pd.to_numeric(text, errors="coerce")

def normalize_business_data(raw, mapping, dayfirst=False):
    validate_mapping(mapping)
    data = pd.DataFrame(index=raw.index)
    for field, column in mapping.items():
        if column is not None:
            if column not in raw.columns:
                raise ValueError(f"Missing mapped column: {column}")
            data[field] = raw[column]

    data["Date"] = pd.to_datetime(data["Date"], errors="coerce", dayfirst=dayfirst)
    for col in ["Revenue", "Quantity", "UnitPrice"]:
        if col in data:
            data[col] = parse_amount(data[col])

    if "Revenue" not in data:
        data["Revenue"] = data["Quantity"] * data["UnitPrice"]

    text_columns = ["OrderID", "Product", "Category", "CustomerID", "Store", "Country"]
    for col in text_columns:
        if col in data:
            data[col] = data[col].astype("string").str.strip().replace("", pd.NA)

    invalid_date = data["Date"].isna()
    invalid_revenue = data["Revenue"].isna() | ~data["Revenue"].apply(lambda x: pd.notna(x) and abs(x) != float("inf"))
    invalid = invalid_date | invalid_revenue
    cleaned = data.loc[~invalid].copy()
    cleaned["Month"] = cleaned["Date"].dt.to_period("M").dt.to_timestamp()
    cleaned["Year"] = cleaned["Date"].dt.year
    cleaned["Weekday"] = cleaned["Date"].dt.day_name()
    cleaned["SalesType"] = cleaned["Revenue"].ge(0).map({True: "Nonnegative", False: "Negative"})
    cleaned = cleaned.reset_index(drop=True)

    quality = {
        "OriginalRows": len(raw),
        "ValidRows": len(cleaned),
        "ExcludedRows": int(invalid.sum()),
        "InvalidDates": int(invalid_date.sum()),
        "InvalidRevenue": int(invalid_revenue.sum()),
        "NegativeRevenueRows": int((cleaned["Revenue"] < 0).sum()),
        "MissingOrderIDs": int(cleaned["OrderID"].isna().sum()) if "OrderID" in cleaned else None,
        "MissingCustomerIDs": int(cleaned["CustomerID"].isna().sum()) if "CustomerID" in cleaned else None
    }
    return cleaned, quality