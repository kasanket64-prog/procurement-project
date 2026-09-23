import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
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
# 3. SORT BY DATE
# ==========================================

df = df.sort_values(
    ["order_date", "po_id"]
).reset_index(drop=True)


# ==========================================
# 4. TARGET
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

df["order_month"] = df["order_date"].dt.month
df["order_dayofweek"] = df["order_date"].dt.dayofweek


# ==========================================
# 6. SUPPLIER PREVIOUS ORDER COUNT
# ==========================================

group = df.groupby("supplier_id")

df["supplier_previous_orders"] = (
    group.cumcount()
)


# ==========================================
# 7. HISTORICAL LATE RATE
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
# 8. HISTORICAL AVG DELAY
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
# 9. HISTORICAL AVG QUANTITY
# ==========================================

df["previous_quantity_sum"] = (
    group["quantity"].cumsum()
    - df["quantity"]
)

df["supplier_avg_quantity"] = (
    df["previous_quantity_sum"]
    / df["supplier_previous_orders"]
)


# ==========================================
# 10. QUANTITY RELATIVE TO HISTORY
# ==========================================

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
# 15. HANDLE NEW SUPPLIERS
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
    .replace([float("inf"), float("-inf")], pd.NA)
)

for column in history_features:
    df[column] = df[column].fillna(
        df[column].median()
    )


# ==========================================
# 16. FEATURES
# ==========================================

features = [
    "supplier_id",
    "supplier_country",
    "category",
    "item",
    "business_unit",
    "payment_terms",

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

X = df[features]
y = df["late_delivery"]


# ==========================================
# 17. TIME BASED SPLIT
# ==========================================

split_index = int(len(df) * 0.80)

X_train = X.iloc[:split_index]
X_test = X.iloc[split_index:]

y_train = y.iloc[:split_index]
y_test = y.iloc[split_index:]


print("\nTIME BASED SPLIT")

print("Training:", len(X_train))
print("Testing:", len(X_test))

print(
    "Train period:",
    df["order_date"].iloc[0],
    "to",
    df["order_date"].iloc[split_index - 1]
)

print(
    "Test period:",
    df["order_date"].iloc[split_index],
    "to",
    df["order_date"].iloc[-1]
)


# ==========================================
# 18. FEATURE TYPES
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
    column
    for column in features
    if column not in categorical_features
]


# ==========================================
# 19. PREPROCESSING
# ==========================================

preprocessor = ColumnTransformer(
    transformers=[
        (
            "categorical",
            OneHotEncoder(
                handle_unknown="ignore"
            ),
            categorical_features
        ),

        (
            "numeric",
            "passthrough",
            numeric_features
        )
    ]
)


# ==========================================
# 20. RANDOM FOREST
# ==========================================
model = CatBoostClassifier(
    iterations=500,
    depth=6,
    learning_rate=0.05,
    loss_function="Logloss",
    auto_class_weights="Balanced",
    random_seed=42,
    verbose=100
)

# ==========================================
# 21. PIPELINE
# ==========================================

pipeline = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        ("model", model)
    ]
)


# ==========================================
# 22. TRAIN
# ==========================================

print("\nTraining CatBoost...")

pipeline.fit(
    X_train,
    y_train
)

print("Training completed!")


# ==========================================
# 23. PREDICT
# ==========================================

predictions = pipeline.predict(
    X_test
)

probabilities = pipeline.predict_proba(
    X_test
)[:, 1]


# ==========================================
# 24. RESULTS
# ==========================================

print("\n==========================")
print("V3 MODEL RESULTS")
print("==========================")

print(
    "Accuracy:",
    accuracy_score(y_test, predictions)
)

print(
    "Precision:",
    precision_score(y_test, predictions)
)

print(
    "Recall:",
    recall_score(y_test, predictions)
)

print(
    "F1:",
    f1_score(y_test, predictions)
)

print(
    "ROC-AUC:",
    roc_auc_score(y_test, probabilities)
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

for threshold in [
    0.5,
    0.45,
    0.4,
    0.35,
    0.3
]:

    threshold_predictions = (
        probabilities >= threshold
    ).astype(int)

    print("\nThreshold:", threshold)

    print(
        "Precision:",
        precision_score(
            y_test,
            threshold_predictions
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

trained_preprocessor = (
    pipeline.named_steps["preprocessor"]
)

trained_model = (
    pipeline.named_steps["model"]
)

feature_names = (
    trained_preprocessor
    .get_feature_names_out()
)

importance = (
    trained_model.feature_importances_
)

importance_df = pd.DataFrame({
    "feature": feature_names,
    "importance": importance
})

importance_df = importance_df.sort_values(
    "importance",
    ascending=False
)

print(
    importance_df.head(25)
    .to_string(index=False)
)