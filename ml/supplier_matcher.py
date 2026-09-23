import pandas as pd


# ==========================================
# 1. LOAD SUPPLIER-ITEM DATA
# ==========================================

df = pd.read_csv(
    "dataset/supplier_items.csv"
)

print("\nAI Supplier Matching Engine")
print("===========================")

print(
    "Supplier-item records:",
    len(df)
)


# ==========================================
# 2. SHOW PRODUCTS
# ==========================================

items = sorted(
    df["item"]
    .dropna()
    .unique()
)

print("\nAvailable Products:")

for item in items:
    print("-", item)


# ==========================================
# 3. USER REQUIREMENTS
# ==========================================

print("\n===========================")
print("ENTER PROCUREMENT REQUIREMENT")
print("===========================")

product = input(
    "Product: "
).strip()

country = input(
    "Preferred country (Enter for any): "
).strip()

max_price_input = input(
    "Maximum unit price (Enter for any): "
).strip()

quantity_input = input(
    "Required quantity (Enter to skip): "
).strip()


# ==========================================
# 4. CONVERT INPUT
# ==========================================

max_price = None

if max_price_input:
    max_price = float(
        max_price_input
    )


quantity = None

if quantity_input:
    quantity = float(
        quantity_input
    )


# ==========================================
# 5. NORMALIZE PRODUCT TEXT
# ==========================================

def normalize_text(text):

    return (
        str(text)
        .lower()
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
    )


product_normalized = normalize_text(
    product
)

df["item_normalized"] = (
    df["item"]
    .apply(normalize_text)
)


# ==========================================
# 6. PRODUCT MATCHING
# ==========================================

matches = df[
    df["item_normalized"]
    .str.contains(
        product_normalized,
        case=False,
        na=False,
        regex=False
    )
].copy()

# ==========================================
# 6. CHECK PRODUCT
# ==========================================

if matches.empty:

    print(
        "\nNo suppliers found for product:",
        product
    )

    exit()


# ==========================================
# 7. COUNTRY FILTER
# ==========================================

if country:

    matches = matches[
        matches["supplier_country"]
        .str.contains(
            country,
            case=False,
            na=False,
            regex=False
        )
    ]


# ==========================================
# 8. PRICE FILTER
# ==========================================

if max_price is not None:

    matches = matches[
        matches["avg_unit_price"]
        <= max_price
    ]


# ==========================================
# 9. CHECK HARD CONSTRAINTS
# ==========================================

if matches.empty:

    print(
        "\nSuppliers exist for this product,"
        " but none meet all hard constraints."
    )

    print(
        "Try changing country or budget."
    )

    exit()


# ==========================================
# 10. DELIVERY SCORE
# ==========================================

matches["delivery_score"] = (
    matches["on_time_rate"]
)


# ==========================================
# 11. QUALITY SCORE
# ==========================================

matches["quality_score"] = (

    100
    - matches["rejection_rate"]

)


# ==========================================
# 12. EXPERIENCE SCORE
# ==========================================

max_orders = (
    matches["historical_orders"]
    .max()
)

if max_orders > 0:

    matches["experience_score"] = (

        matches["historical_orders"]

        / max_orders

        * 100
    )

else:

    matches["experience_score"] = 0


# ==========================================
# 13. PRICE SCORE
# ==========================================

if max_price is not None:

    matches["price_score"] = (

        (
            max_price
            - matches["avg_unit_price"]
        )

        / max_price

        * 100
    )

    matches["price_score"] = (
        matches["price_score"]
        .clip(
            lower=0,
            upper=100
        )
    )

else:

    cheapest = (
        matches["avg_unit_price"]
        .min()
    )

    matches["price_score"] = (

        cheapest

        / matches["avg_unit_price"]

        * 100
    )


# ==========================================
# 14. QUANTITY INFORMATION
# ==========================================

if quantity is not None:

    matches["quantity_vs_history"] = (

        quantity

        / matches[
            "max_historical_quantity"
        ]
    )

else:

    matches["quantity_vs_history"] = 0


# ==========================================
# 15. FINAL MATCH SCORE
# ==========================================

matches["match_score"] = (

    matches["delivery_score"] * 0.40

    +

    matches["quality_score"] * 0.30

    +

    matches["experience_score"] * 0.20

    +

    matches["price_score"] * 0.10

)


# ==========================================
# 16. HISTORICAL RISK LABEL
# ==========================================

def risk_level(rate):

    if rate < 15:
        return "LOW"

    elif rate < 30:
        return "MEDIUM"

    else:
        return "HIGH"


matches["historical_risk"] = (

    matches["late_delivery_rate"]
    .apply(risk_level)

)


# ==========================================
# 17. SORT
# ==========================================

matches = matches.sort_values(
    "match_score",
    ascending=False
)


# ==========================================
# 18. DISPLAY
# ==========================================

print("\n===========================")
print("RECOMMENDED SUPPLIERS")
print("===========================")

print(
    "\nProduct:",
    product
)

if quantity is not None:

    print(
        "Required Quantity:",
        quantity
    )

if max_price is not None:

    print(
        "Maximum Unit Price:",
        max_price
    )

print(
    "Suppliers Found:",
    len(matches)
)


top_matches = (
    matches.head(10)
)


for rank, (_, supplier) in enumerate(
    top_matches.iterrows(),
    start=1
):

    print(
        "\n---------------------------"
    )

    print(
        f"#{rank} "
        f"{supplier['supplier_name']}"
    )

    print(
        "Supplier ID:",
        supplier["supplier_id"]
    )

    print(
        "Country:",
        supplier["supplier_country"]
    )

    print(
        "Item:",
        supplier["item"]
    )

    print(
        "Match Score:",
        round(
            supplier["match_score"],
            2
        ),
        "%"
    )

    print(
        "Average Unit Price:",
        supplier["avg_unit_price"]
    )

    print(
        "Historical Price Range:",
        supplier["min_unit_price"],
        "-",
        supplier["max_unit_price"]
    )

    print(
        "On-Time Rate:",
        supplier["on_time_rate"],
        "%"
    )

    print(
        "Late Delivery Rate:",
        supplier["late_delivery_rate"],
        "%"
    )

    print(
        "Quality Rejection Rate:",
        supplier["rejection_rate"],
        "%"
    )

    print(
        "Historical Orders:",
        supplier["historical_orders"]
    )

    print(
        "Largest Historical Order:",
        supplier[
            "max_historical_quantity"
        ]
    )

    if quantity is not None:

        if (
            quantity
            <= supplier[
                "max_historical_quantity"
            ]
        ):

            print(
                "Quantity History:",
                "Previously handled"
            )

        else:

            print(
                "Quantity History:",
                "Above largest observed order"
            )

    print(
        "Historical Risk:",
        supplier[
            "historical_risk"
        ]
    )