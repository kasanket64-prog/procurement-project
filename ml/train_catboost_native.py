import pandas as pd
import numpy as np

from catboost import CatBoostClassifier

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix
)


# ==========================================
# 1. LOAD DATA
# ==========================================

df = pd.read_csv("dataset/procurement.csv")

print("Dataset loaded!")
print("Shape:", df.shape)


# ==========================================
# 2. CONVERT DATES
# ==========================================

date_columns = [
    "order_date",
    "promised_delivery_date",
    "actual_delivery_date"
]

for column in date_columns:
    df[column] = pd.to_datetime(df[column])


# ==========================================
# 3. SORT DATA
# ==========================================

df = df.sort_values(
    ["order_date", "po_id"]
).reset_index(drop=True)


# ==========================================
# 4. CREATE TARGET
# ==========================================

df["delivery_delay_days"] = (
    df["actual_delivery_date"]
    - df["promised_delivery_date"]
).dt.days

df["late_delivery"] = (
    df["delivery_delay_days"] > 0
).astype(int)


# ==========================================
# 5. CURRENT ORDER FEATURES
# ==========================================

df["promised_lead_days"] = (
    df["promised_delivery_date"]
    - df["order_date"]
).dt.days

df["order_month"] = (
    df["order_date"].dt.month
)

df["order_dayofweek"] = (
    df["order_date"].dt.dayofweek
)


# ==========================================
# 6. SUPPLIER GROUP
# ==========================================

group = df.groupby("supplier_id")


# ==========================================
# 7. PREVIOUS ORDER COUNT
# ==========================================

df["supplier_previous_orders"] = (
    group.cumcount()
)


# ==========================================
# 8. HISTORICAL LATE RATE
# ==========================================

df["supplier_previous_late"] = (
    group["late_delivery"].cumsum()
    - df["late_delivery"]
)

df["supplier_late_rate"] = (
    df["supplier_previous_late"]
    / df["supplier_previous_orders"]
)


# ==========================================
# 9. HISTORICAL AVG DELAY
# ==========================================

df["previous_delay_sum"] = (
    group["delivery_delay_days"].cumsum()
    - df["delivery_delay_days"]
)

df["supplier_avg_delay"] = (
    df["previous_delay_sum"]
    / df["supplier_previous_orders"]
)


# ==========================================
# 10. HISTORICAL AVG QUANTITY
# ==========================================

df["previous_quantity_sum"] = (
    group["quantity"].cumsum()
    - df["quantity"]
)

df["supplier_avg_quantity"] = (
    df["previous_quantity_sum"]
    / df["supplier_previous_orders"]
)

df["quantity_vs_supplier_avg"] = (
    df["quantity"]
    / df["supplier_avg_quantity"]
)


# ==========================================
# 11. HISTORICAL AVG PRICE
# ==========================================

df["previous_price_sum"] = (
    group["unit_price"].cumsum()
    - df["unit_price"]
)

df["supplier_avg_price"] = (
    df["previous_price_sum"]
    / df["supplier_previous_orders"]
)

df["price_vs_supplier_avg"] = (
    df["unit_price"]
    / df["supplier_avg_price"]
)


# ==========================================
# 12. HISTORICAL AVG LEAD TIME
# ==========================================

df["previous_lead_sum"] = (
    group["promised_lead_days"].cumsum()
    - df["promised_lead_days"]
)

df["supplier_avg_lead"] = (
    df["previous_lead_sum"]
    / df["supplier_previous_orders"]
)

df["lead_time_vs_supplier_avg"] = (
    df["promised_lead_days"]
    / df["supplier_avg_lead"]
)


# ==========================================
# 13. HISTORICAL AVG ORDER VALUE
# ==========================================

df["previous_value_sum"] = (
    group["line_total"].cumsum()
    - df["line_total"]
)

df["supplier_avg_order_value"] = (
    df["previous_value_sum"]
    / df["supplier_previous_orders"]
)

df["value_vs_supplier_avg"] = (
    df["line_total"]
    / df["supplier_avg_order_value"]
)


# ==========================================
# 14. HISTORICAL QUALITY RATE
# ==========================================

df["quality_rejected_int"] = (
    df["quality_rejected"].astype(int)
)

df["previous_rejections"] = (
    group["quality_rejected_int"].cumsum()
    - df["quality_rejected_int"]
)

df["supplier_rejection_rate"] = (
    df["previous_rejections"]
    / df["supplier_previous_orders"]
)


# ==========================================
# 15. HANDLE MISSING / INFINITE VALUES
# ==========================================

history_features = [
    "supplier_late_rate",
    "supplier_avg_delay",
    "supplier_avg_quantity",
    "quantity_vs_supplier_avg",
    "supplier_avg_price",
    "price_vs_supplier_avg",
    "supplier_avg_lead",
    "lead_time_vs_supplier_avg",
    "supplier_avg_order_value",
    "value_vs_supplier_avg",
    "supplier_rejection_rate"
]

df[history_features] = (
    df[history_features]
    .replace([np.inf, -np.inf], np.nan)
)

for column in history_features:

    df[column] = (
        df[column]
        .fillna(df[column].median())
    )


# ==========================================
# 16. SELECT FEATURES
# ==========================================

categorical_features = [
    "supplier_id",
    "supplier_country",
    "category",
    "item",
    "business_unit",
    "payment_terms"
]

numeric_features = [
    "unit_price",
    "quantity",
    "line_total",
    "on_contract",
    "promised_lead_days",

    "supplier_previous_orders",
    "supplier_late_rate",
    "supplier_avg_delay",

    "quantity_vs_supplier_avg",
    "price_vs_supplier_avg",
    "lead_time_vs_supplier_avg",
    "value_vs_supplier_avg",

    "supplier_rejection_rate",

    "order_month",
    "order_dayofweek"
]

features = (
    categorical_features
    + numeric_features
)

X = df[features].copy()

y = df["late_delivery"]


# ==========================================
# 17. CONVERT CATEGORIES TO STRING
# ==========================================

for column in categorical_features:

    X[column] = (
        X[column]
        .fillna("Unknown")
        .astype(str)
    )


# ==========================================
# 18. BOOLEAN TO INTEGER
# ==========================================

X["on_contract"] = (
    X["on_contract"].astype(int)
)


# ==========================================
# 19. TIME-BASED SPLIT
# ==========================================

split_index = int(
    len(df) * 0.80
)

X_train = (
    X.iloc[:split_index]
    .copy()
)

X_test = (
    X.iloc[split_index:]
    .copy()
)

y_train = (
    y.iloc[:split_index]
    .copy()
)

y_test = (
    y.iloc[split_index:]
    .copy()
)


print("\nTIME BASED SPLIT")

print(
    "Training:",
    len(X_train)
)

print(
    "Testing:",
    len(X_test)
)

print(
    "Train period:",
    df["order_date"].iloc[0],
    "to",
    df["order_date"].iloc[
        split_index - 1
    ]
)

print(
    "Test period:",
    df["order_date"].iloc[
        split_index
    ],
    "to",
    df["order_date"].iloc[-1]
)


# ==========================================
# 20. FIND CATEGORY COLUMN POSITIONS
# ==========================================

cat_feature_indices = [

    X.columns.get_loc(column)

    for column
    in categorical_features
]


# ==========================================
# 21. CATBOOST MODEL
# ==========================================

model = CatBoostClassifier(

    iterations=700,

    depth=6,

    learning_rate=0.05,

    loss_function="Logloss",

    eval_metric="AUC",

    auto_class_weights="Balanced",

    random_seed=42,

    verbose=100
)


# ==========================================
# 22. TRAIN
# ==========================================

print(
    "\nTraining Native CatBoost..."
)

model.fit(

    X_train,

    y_train,

    cat_features=cat_feature_indices,

    eval_set=(
        X_test,
        y_test
    ),

    early_stopping_rounds=75,

    verbose=100
)

print(
    "Training completed!"
)


# ==========================================
# 23. PREDICTIONS
# ==========================================

probabilities = (
    model.predict_proba(X_test)[:, 1]
)

predictions = (
    probabilities >= 0.5
).astype(int)


# ==========================================
# 24. RESULTS
# ==========================================

print("\n==========================")
print("NATIVE CATBOOST RESULTS")
print("==========================")

print(
    "Accuracy:",
    accuracy_score(
        y_test,
        predictions
    )
)

print(
    "Precision:",
    precision_score(
        y_test,
        predictions
    )
)

print(
    "Recall:",
    recall_score(
        y_test,
        predictions
    )
)

print(
    "F1:",
    f1_score(
        y_test,
        predictions
    )
)

print(
    "ROC-AUC:",
    roc_auc_score(
        y_test,
        probabilities
    )
)

print(
    "PR-AUC:",
    average_precision_score(
        y_test,
        probabilities
    )
)


print("\nConfusion Matrix:")

print(
    confusion_matrix(
        y_test,
        predictions
    )
)


# ==========================================
# 25. THRESHOLD TEST
# ==========================================

print("\n==========================")
print("THRESHOLD TEST")
print("==========================")

thresholds = [
    0.60,
    0.55,
    0.50,
    0.45,
    0.40,
    0.35,
    0.30
]

for threshold in thresholds:

    threshold_predictions = (
        probabilities >= threshold
    ).astype(int)

    print(
        "\nThreshold:",
        threshold
    )

    print(
        "Precision:",
        precision_score(
            y_test,
            threshold_predictions,
            zero_division=0
        )
    )

    print(
        "Recall:",
        recall_score(
            y_test,
            threshold_predictions
        )
    )

    print(
        "F1:",
        f1_score(
            y_test,
            threshold_predictions
        )
    )

    print(
        confusion_matrix(
            y_test,
            threshold_predictions
        )
    )


# ==========================================
# 26. FEATURE IMPORTANCE
# ==========================================

print("\n==========================")
print("TOP FEATURE IMPORTANCE")
print("==========================")

importance_df = pd.DataFrame({

    "feature": features,

    "importance":
        model.get_feature_importance()

})

importance_df = (
    importance_df
    .sort_values(
        "importance",
        ascending=False
    )
)

print(
    importance_df
    .head(20)
    .to_string(index=False)
)