import pandas as pd


# ==========================================
# 1. LOAD DATA
# ==========================================

df = pd.read_csv(
    "dataset/procurement.csv"
)

print("Dataset loaded!")
print("Orders:", len(df))


# ==========================================
# 2. CONVERT DATES
# ==========================================

df["promised_delivery_date"] = pd.to_datetime(
    df["promised_delivery_date"]
)

df["actual_delivery_date"] = pd.to_datetime(
    df["actual_delivery_date"]
)


# ==========================================
# 3. DELIVERY FEATURES
# ==========================================

df["delivery_delay_days"] = (
    df["actual_delivery_date"]
    - df["promised_delivery_date"]
).dt.days

df["late_delivery"] = (
    df["delivery_delay_days"] > 0
).astype(int)

df["quality_rejected_int"] = (
    df["quality_rejected"].astype(int)
)


# ==========================================
# 4. SUPPLIER + ITEM MASTER
# ==========================================

supplier_items = (
    df.groupby(
        [
            "supplier_id",
            "supplier_name",
            "supplier_country",
            "category",
            "item"
        ]
    )
    .agg(

        historical_orders=(
            "po_id",
            "count"
        ),

        avg_unit_price=(
            "unit_price",
            "mean"
        ),

        min_unit_price=(
            "unit_price",
            "min"
        ),

        max_unit_price=(
            "unit_price",
            "max"
        ),

        avg_quantity=(
            "quantity",
            "mean"
        ),

        max_historical_quantity=(
            "quantity",
            "max"
        ),

        avg_order_value=(
            "line_total",
            "mean"
        ),

        late_delivery_rate=(
            "late_delivery",
            "mean"
        ),

        avg_delivery_delay=(
            "delivery_delay_days",
            "mean"
        ),

        rejection_rate=(
            "quality_rejected_int",
            "mean"
        )

    )
    .reset_index()
)


# ==========================================
# 5. ON-TIME RATE
# ==========================================

supplier_items["on_time_rate"] = (
    1
    - supplier_items["late_delivery_rate"]
)


# ==========================================
# 6. CONVERT TO PERCENT
# ==========================================

supplier_items["late_delivery_rate"] *= 100

supplier_items["on_time_rate"] *= 100

supplier_items["rejection_rate"] *= 100


# ==========================================
# 7. ROUND VALUES
# ==========================================

numeric_columns = [

    "avg_unit_price",
    "min_unit_price",
    "max_unit_price",

    "avg_quantity",
    "max_historical_quantity",

    "avg_order_value",

    "late_delivery_rate",
    "on_time_rate",

    "avg_delivery_delay",

    "rejection_rate"
]


supplier_items[numeric_columns] = (
    supplier_items[numeric_columns]
    .round(2)
)


# ==========================================
# 8. SAVE
# ==========================================

output_file = (
    "dataset/supplier_items.csv"
)

supplier_items.to_csv(
    output_file,
    index=False
)


# ==========================================
# 9. DISPLAY
# ==========================================

print(
    "\nSupplier-item master created!"
)

print(
    "Supplier-item combinations:",
    len(supplier_items)
)

print(
    "\nColumns:"
)

print(
    supplier_items.columns.tolist()
)

print(
    "\nSample:"
)

print(
    supplier_items
    .head(10)
    .to_string(index=False)
)

print(
    "\nSaved to:",
    output_file
)