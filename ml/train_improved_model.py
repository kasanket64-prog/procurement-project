import os
import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    classification_report
)


# ==========================================
# 1. LOAD DATASET
# ==========================================

df = pd.read_csv(
    "dataset/procurement.csv"
)

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
    df[column] = pd.to_datetime(
        df[column]
    )


# ==========================================
# 3. CREATE TARGET
# ==========================================

df["delivery_delay_days"] = (
    df["actual_delivery_date"]
    - df["promised_delivery_date"]
).dt.days

df["late_delivery"] = (
    df["delivery_delay_days"] > 0
).astype(int)

df["promised_lead_days"] = (
    df["promised_delivery_date"]
    - df["order_date"]
).dt.days


# ==========================================
# 4. SORT DATA
# ==========================================

df = (
    df.sort_values(
        ["order_date", "po_id"]
    )
    .reset_index(drop=True)
)

print("\nDataset sorted by date.")


# ==========================================
# 5. BUILD SUPPLIER-DATE HISTORY
# ==========================================
#
# IMPORTANT:
# Orders from the SAME DATE must receive
# identical supplier history.
#
# Only dates STRICTLY BEFORE the current
# order date are used.
# ==========================================

daily = (
    df.groupby(
        [
            "supplier_id",
            "order_date"
        ],
        as_index=False
    )
    .agg(
        daily_orders=(
            "po_id",
            "count"
        ),
        daily_late=(
            "late_delivery",
            "sum"
        ),
        daily_delay_sum=(
            "delivery_delay_days",
            "sum"
        )
    )
)


daily = (
    daily.sort_values(
        [
            "supplier_id",
            "order_date"
        ]
    )
    .reset_index(drop=True)
)


# ==========================================
# 6. STRICTLY PREVIOUS HISTORY
# ==========================================

daily["supplier_previous_orders"] = (
    daily.groupby(
        "supplier_id"
    )["daily_orders"]
    .cumsum()
    - daily["daily_orders"]
)


daily["supplier_previous_late"] = (
    daily.groupby(
        "supplier_id"
    )["daily_late"]
    .cumsum()
    - daily["daily_late"]
)


daily["supplier_previous_delay_sum"] = (
    daily.groupby(
        "supplier_id"
    )["daily_delay_sum"]
    .cumsum()
    - daily["daily_delay_sum"]
)


# ==========================================
# 7. HISTORICAL RATES
# ==========================================

daily["supplier_late_rate"] = (
    daily["supplier_previous_late"]
    / daily["supplier_previous_orders"]
)

daily["supplier_avg_delay"] = (
    daily["supplier_previous_delay_sum"]
    / daily["supplier_previous_orders"]
)


daily["supplier_late_rate"] = (
    daily["supplier_late_rate"]
    .fillna(0)
)

daily["supplier_avg_delay"] = (
    daily["supplier_avg_delay"]
    .fillna(0)
)


# ==========================================
# 8. MERGE HISTORY BACK TO ORDERS
# ==========================================

history_columns = [
    "supplier_id",
    "order_date",
    "supplier_previous_orders",
    "supplier_previous_late",
    "supplier_previous_delay_sum",
    "supplier_late_rate",
    "supplier_avg_delay"
]


df = df.merge(
    daily[history_columns],
    on=[
        "supplier_id",
        "order_date"
    ],
    how="left"
)


# ==========================================
# 9. DATE FEATURES
# ==========================================

df["order_month"] = (
    df["order_date"].dt.month
)

df["order_dayofweek"] = (
    df["order_date"].dt.dayofweek
)


# ==========================================
# 10. VERIFY SAME-DAY PROTECTION
# ==========================================

print(
    "\n=========================="
)

print(
    "SAME-DAY LEAKAGE CHECK"
)

print(
    "=========================="
)


check = (
    df[
        [
            "order_date",
            "supplier_id",
            "supplier_previous_orders",
            "supplier_previous_late",
            "supplier_late_rate",
            "supplier_avg_delay"
        ]
    ]
    .head(20)
)

print(check)


# ==========================================
# 11. MODEL FEATURES
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
    "order_month",
    "order_dayofweek"
]


features = (
    categorical_features
    + numeric_features
)


X = df[features].copy()

y = df[
    "late_delivery"
].copy()


# ==========================================
# 12. TIME-BASED SPLIT
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


print(
    "\n=========================="
)

print(
    "TIME BASED SPLIT"
)

print(
    "=========================="
)

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
# 13. PREPROCESSOR
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
# 14. RANDOM FOREST
# ==========================================

model = RandomForestClassifier(
    n_estimators=300,
    random_state=42,
    class_weight="balanced",
    n_jobs=-1
)


# ==========================================
# 15. PIPELINE
# ==========================================

pipeline = Pipeline(
    steps=[
        (
            "preprocessor",
            preprocessor
        ),

        (
            "model",
            model
        )
    ]
)


# ==========================================
# 16. TRAIN
# ==========================================

print(
    "\nTraining leakage-free model..."
)

pipeline.fit(
    X_train,
    y_train
)

print(
    "Training completed!"
)


# ==========================================
# 17. PREDICT
# ==========================================

probabilities = (
    pipeline.predict_proba(
        X_test
    )[:, 1]
)

predictions = (
    probabilities >= 0.5
).astype(int)


# ==========================================
# 18. RESULTS
# ==========================================

print(
    "\n=========================="
)

print(
    "LEAKAGE-FREE MODEL RESULTS"
)

print(
    "=========================="
)


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
        predictions,
        zero_division=0
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


print(
    "\nConfusion Matrix:"
)

print(
    confusion_matrix(
        y_test,
        predictions
    )
)


print(
    "\nClassification Report:"
)

print(
    classification_report(
        y_test,
        predictions,
        zero_division=0
    )
)


# ==========================================
# 19. THRESHOLD TEST
# ==========================================

print(
    "\n=========================="
)

print(
    "THRESHOLD TEST"
)

print(
    "=========================="
)


thresholds = [
    0.50,
    0.40,
    0.30,
    0.20
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
# 20. SAVE CLEAN MODEL
# ==========================================

os.makedirs(
    "models",
    exist_ok=True
)


model_path = (
    "models/"
    "delivery_risk_model_clean.pkl"
)


joblib.dump(
    pipeline,
    model_path
)


print(
    "\n=========================="
)

print(
    "CLEAN MODEL SAVED"
)

print(
    "=========================="
)

print(
    "Saved to:",
    model_path
)


if os.path.exists(
    model_path
):

    size_mb = (
        os.path.getsize(
            model_path
        )
        / (1024 * 1024)
    )

    print(
        "File size:",
        round(
            size_mb,
            2
        ),
        "MB"
    )