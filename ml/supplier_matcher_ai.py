import pandas as pd
import joblib
from datetime import datetime


# ==========================================
# 1. LOAD SUPPLIER-ITEM DATA
# ==========================================

df = pd.read_csv(
    "dataset/supplier_items.csv"
)
supplier_history = pd.read_csv(
    "dataset/supplier_history.csv"
)
print("\nAI Supplier Matching Engine")
print("===========================")

print(
    "Supplier-item records:",
    len(df)
)


# ==========================================
# 2. LOAD TRAINED AI MODEL
# ==========================================

risk_model = joblib.load(
    "models/delivery_risk_model_clean.pkl"
)

print(
    "AI delivery-risk model loaded!"
)


# ==========================================
# 3. SHOW AVAILABLE PRODUCTS
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
# 4. BUYER REQUIREMENTS
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
    "Required quantity: "
).strip()

lead_days_input = input(
    "Required delivery days: "
).strip()

business_unit = input(
    "Business unit (e.g. Manufacturing): "
).strip()

payment_terms = input(
    "Payment terms (e.g. Net 30): "
).strip()

contract_input = input(
    "On contract? (yes/no): "
).strip().lower()
print("\n===========================")
print("SET BUYER PRIORITIES")
print("===========================")

print("Enter importance from 0 to 100.")
print("The system will automatically normalize the weights.")

delivery_weight = float(
    input("Delivery importance: ")
)

quality_weight = float(
    input("Quality importance: ")
)

experience_weight = float(
    input("Experience importance: ")
)

price_weight = float(
    input("Price importance: ")
)
total_weight = (
    delivery_weight
    + quality_weight
    + experience_weight
    + price_weight
)

if total_weight <= 0:
    print("\nPriority weights cannot all be 0.")
    exit()

delivery_weight = (
    delivery_weight / total_weight
)

quality_weight = (
    quality_weight / total_weight
)

experience_weight = (
    experience_weight / total_weight
)

price_weight = (
    price_weight / total_weight
)

print("\nNormalized Priorities:")

print(
    "Delivery:",
    round(delivery_weight * 100, 2),
    "%"
)

print(
    "Quality:",
    round(quality_weight * 100, 2),
    "%"
)

print(
    "Experience:",
    round(experience_weight * 100, 2),
    "%"
)

print(
    "Price:",
    round(price_weight * 100, 2),
    "%"
)

# ==========================================
# 5. CONVERT BUYER INPUT
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


promised_lead_days = int(
    lead_days_input
)


on_contract = (
    1
    if contract_input == "yes"
    else 0
)


# ==========================================
# 6. NORMALIZE PRODUCT TEXT
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
# 7. PRODUCT MATCHING
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


if matches.empty:

    print(
        "\nNo suppliers found for product:",
        product
    )

    exit()


# ==========================================
# 8. COUNTRY FILTER
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
# 9. PRICE FILTER
# ==========================================

if max_price is not None:

    matches = matches[
        matches["avg_unit_price"]
        <= max_price
    ]


if matches.empty:

    print(
        "\nSuppliers exist for this product,"
        " but none meet the country/budget "
        "requirements."
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
# 14. DYNAMIC MATCH SCORE
# ==========================================

matches["match_score"] = (
    matches["delivery_score"]
    * delivery_weight

    + matches["quality_score"]
    * quality_weight

    + matches["experience_score"]
    * experience_weight

    + matches["price_score"]
    * price_weight
)

# ==========================================
# 15. HISTORICAL RISK
# ==========================================

def historical_risk(rate):

    if rate < 15:
        return "LOW"

    elif rate < 30:
        return "MEDIUM"

    else:
        return "HIGH"


matches["historical_risk"] = (

    matches["late_delivery_rate"]
    .apply(historical_risk)

)


# # ==========================================
# 16. AI DELIVERY-RISK FUNCTION
# ==========================================

def predict_delivery_risk(supplier):

    unit_price = float(
        supplier["avg_unit_price"]
    )

    if quantity is not None:
        order_quantity = quantity
    else:
        order_quantity = float(
            supplier["avg_quantity"]
        )

    line_total = (
        unit_price * order_quantity
    )

    # Get supplier-wide historical data
    history = supplier_history[
        supplier_history["supplier_id"]
        == supplier["supplier_id"]
    ]

    if history.empty:
        previous_orders = 0
        supplier_late_rate = 0.0
        supplier_avg_delay = 0.0

    else:
        history = history.iloc[0]

        previous_orders = int(
            history["supplier_previous_orders"]
        )

        supplier_late_rate = float(
            history["supplier_late_rate"]
        )

        supplier_avg_delay = float(
            history["supplier_avg_delay"]
        )

    today = datetime.now()

    prediction_data = pd.DataFrame(
        [{
            "supplier_id":
                supplier["supplier_id"],

            "supplier_country":
                supplier["supplier_country"],

            "category":
                supplier["category"],

            "item":
                supplier["item"],

            "business_unit":
                business_unit,

            "payment_terms":
                payment_terms,

            "unit_price":
                unit_price,

            "quantity":
                order_quantity,

            "line_total":
                line_total,

            "on_contract":
                on_contract,

            "promised_lead_days":
                promised_lead_days,

            "supplier_previous_orders":
                previous_orders,

            "supplier_late_rate":
                supplier_late_rate,

            "supplier_avg_delay":
                supplier_avg_delay,

            "order_month":
                today.month,

            "order_dayofweek":
                today.weekday()
        }]
    )

    probability = (
        risk_model
        .predict_proba(
            prediction_data
        )[0][1]
    )

    return probability * 100
# ==========================================
# 17. RUN AI FOR EACH SUPPLIER
# ==========================================

print("\nCalculating AI delivery risk...")

matches["ai_late_risk"] = matches.apply(
    predict_delivery_risk,
    axis=1
)


# ==========================================
# 18. SORT RESULTS
# ==========================================

matches = matches.sort_values(
    "match_score",
    ascending=False
)


# ==========================================
# 19. DISPLAY RESULTS
# ==========================================

print("\n===========================")
print("AI RECOMMENDED SUPPLIERS")
print("===========================")

print("\nProduct:", product)

if quantity is not None:
    print("Required Quantity:", quantity)

print(
    "Delivery Requirement:",
    promised_lead_days,
    "days"
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

top_matches = matches.head(10)

for rank, (_, supplier) in enumerate(
    top_matches.iterrows(),
    start=1
):

    print("\n---------------------------")

    print(
        f"#{rank} {supplier['supplier_name']}"
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
        "AI Late-Delivery Risk Score:",
        round(
            supplier["ai_late_risk"],
            2
        ),
        "%"
    )

    print(
        "Historical Risk:",
        supplier["historical_risk"]
    )

    print(
        "Historical Late Rate (Item):",
        supplier["late_delivery_rate"],
        "%"
    )

    print(
        "On-Time Rate:",
        supplier["on_time_rate"],
        "%"
    )

    print(
        "Quality Rejection Rate:",
        supplier["rejection_rate"],
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
        "Product-Specific Historical Orders:",
        supplier["historical_orders"]
    )

    print(
        "Largest Historical Order:",
        supplier["max_historical_quantity"]
    )

    if quantity is not None:

        if (
            quantity
            <= supplier["max_historical_quantity"]
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