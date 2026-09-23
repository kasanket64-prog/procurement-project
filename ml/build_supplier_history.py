import pandas as pd


# ==========================================
# 1. LOAD PROCUREMENT DATA
# ==========================================

df = pd.read_csv(
    "dataset/procurement.csv"
)

print("Dataset loaded!")
print("Orders:", len(df))


# ==========================================
# 2. CONVERT DATES
# ==========================================

df["order_date"] = pd.to_datetime(
    df["order_date"]
)

df["promised_delivery_date"] = pd.to_datetime(
    df["promised_delivery_date"]
)

df["actual_delivery_date"] = pd.to_datetime(
    df["actual_delivery_date"]
)


# ==========================================
# 3. DELIVERY DELAY
# ==========================================

df["delivery_delay_days"] = (
    df["actual_delivery_date"]
    - df["promised_delivery_date"]
).dt.days


# ==========================================
# 4. LATE DELIVERY TARGET
# ==========================================

df["late_delivery"] = (
    df["delivery_delay_days"] > 0
).astype(int)


# ==========================================
# 5. BUILD SUPPLIER-WIDE HISTORY
# ==========================================

supplier_history = (
    df.groupby(
        "supplier_id",
        as_index=False
    )
    .agg(
        supplier_previous_orders=(
            "po_id",
            "count"
        ),

        supplier_previous_late=(
            "late_delivery",
            "sum"
        ),

        supplier_avg_delay=(
            "delivery_delay_days",
            "mean"
        )
    )
)


# ==========================================
# 6. HISTORICAL LATE RATE
# ==========================================

supplier_history[
    "supplier_late_rate"
] = (

    supplier_history[
        "supplier_previous_late"
    ]

    /

    supplier_history[
        "supplier_previous_orders"
    ]
)


# ==========================================
# 7. ROUND DISPLAY VALUES
# ==========================================

supplier_history[
    "supplier_avg_delay"
] = (

    supplier_history[
        "supplier_avg_delay"
    ].round(4)
)


supplier_history[
    "supplier_late_rate"
] = (

    supplier_history[
        "supplier_late_rate"
    ].round(6)
)


# ==========================================
# 8. ORDER COLUMNS
# ==========================================

supplier_history = supplier_history[
    [
        "supplier_id",
        "supplier_previous_orders",
        "supplier_previous_late",
        "supplier_late_rate",
        "supplier_avg_delay"
    ]
]


# ==========================================
# 9. SAVE
# ==========================================

output_path = (
    "dataset/supplier_history.csv"
)

supplier_history.to_csv(
    output_path,
    index=False
)


# ==========================================
# 10. DISPLAY
# ==========================================

print("\n==========================")
print("SUPPLIER HISTORY CREATED")
print("==========================")

print(
    "Total suppliers:",
    len(supplier_history)
)

print(
    "\nColumns:"
)

print(
    supplier_history.columns.tolist()
)

print(
    "\nFirst 10 suppliers:"
)

print(
    supplier_history.head(10)
)

print(
    "\nSaved to:",
    output_path
)