import pandas as pd

# ==========================================
# 1. LOAD PROCUREMENT DATA
# ==========================================

df = pd.read_csv("dataset/procurement.csv")

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
# 3. CREATE DELIVERY INFORMATION
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
# 4. BUILD SUPPLIER SUMMARY
# ==========================================

suppliers = (
    df.groupby(
        [
            "supplier_id",
            "supplier_name",
            "supplier_country"
        ]
    )
    .agg(
        total_orders=(
            "po_id",
            "count"
        ),

        avg_unit_price=(
            "unit_price",
            "mean"
        ),

        avg_order_quantity=(
            "quantity",
            "mean"
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
# 5. PRODUCT CATEGORIES
# ==========================================

categories = (
    df.groupby("supplier_id")["category"]
    .apply(
        lambda x:
        ", ".join(
            sorted(
                x.dropna()
                .astype(str)
                .unique()
            )
        )
    )
    .reset_index(
        name="categories"
    )
)


# ==========================================
# 6. ITEMS SUPPLIED
# ==========================================

items = (
    df.groupby("supplier_id")["item"]
    .apply(
        lambda x:
        ", ".join(
            sorted(
                x.dropna()
                .astype(str)
                .unique()
            )
        )
    )
    .reset_index(
        name="items"
    )
)


# ==========================================
# 7. MERGE INFORMATION
# ==========================================

suppliers = suppliers.merge(
    categories,
    on="supplier_id",
    how="left"
)

suppliers = suppliers.merge(
    items,
    on="supplier_id",
    how="left"
)


# ==========================================
# 8. CREATE ON-TIME RATE
# ==========================================

suppliers["on_time_rate"] = (
    1 - suppliers["late_delivery_rate"]
)


# ==========================================
# 9. CONVERT RATES TO PERCENT
# ==========================================

suppliers["late_delivery_rate"] = (
    suppliers["late_delivery_rate"] * 100
)

suppliers["on_time_rate"] = (
    suppliers["on_time_rate"] * 100
)

suppliers["rejection_rate"] = (
    suppliers["rejection_rate"] * 100
)


# ==========================================
# 10. ROUND NUMBERS
# ==========================================

numeric_columns = [
    "avg_unit_price",
    "avg_order_quantity",
    "avg_order_value",
    "late_delivery_rate",
    "on_time_rate",
    "avg_delivery_delay",
    "rejection_rate"
]

suppliers[numeric_columns] = (
    suppliers[numeric_columns]
    .round(2)
)


# ==========================================
# 11. SAVE SUPPLIER MASTER
# ==========================================

output_file = (
    "dataset/suppliers.csv"
)

suppliers.to_csv(
    output_file,
    index=False
)


# ==========================================
# 12. DISPLAY RESULTS
# ==========================================

print("\nSupplier master created!")

print(
    "Total suppliers:",
    len(suppliers)
)

print(
    "\nColumns:"
)

print(
    suppliers.columns.tolist()
)

print(
    "\nSample suppliers:\n"
)

print(
    suppliers.head(10)
    .to_string(index=False)
)

print(
    "\nSaved to:",
    output_file
)