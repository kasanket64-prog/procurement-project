import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix
)

# -----------------------------
# 1. Load dataset
# -----------------------------

df = pd.read_csv("dataset/procurement.csv")

# -----------------------------
# 2. Convert dates
# -----------------------------

df["order_date"] = pd.to_datetime(df["order_date"])
df["promised_delivery_date"] = pd.to_datetime(
    df["promised_delivery_date"]
)
df["actual_delivery_date"] = pd.to_datetime(
    df["actual_delivery_date"]
)

# -----------------------------
# 3. Create target
# -----------------------------

df["delivery_delay_days"] = (
    df["actual_delivery_date"]
    - df["promised_delivery_date"]
).dt.days

df["late_delivery"] = (
    df["delivery_delay_days"] > 0
).astype(int)

# -----------------------------
# 4. Create useful feature
# -----------------------------

df["promised_lead_days"] = (
    df["promised_delivery_date"]
    - df["order_date"]
).dt.days

# -----------------------------
# 5. Select features
# -----------------------------

features = [
    "supplier_id",
    "supplier_country",
    "category",
    "item",
    "business_unit",
    "unit_price",
    "quantity",
    "line_total",
    "payment_terms",
    "on_contract",
    "promised_lead_days"
]

X = df[features]
y = df["late_delivery"]

# -----------------------------
# 6. Categorical columns
# -----------------------------

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
    "promised_lead_days"
]

# -----------------------------
# 7. Preprocessing
# -----------------------------

preprocessor = ColumnTransformer(
    transformers=[
        (
            "category",
            OneHotEncoder(handle_unknown="ignore"),
            categorical_features
        ),
        (
            "number",
            "passthrough",
            numeric_features
        )
    ]
)

# -----------------------------
# 8. Random Forest
# -----------------------------
model = XGBClassifier(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    scale_pos_weight=5.12,
    random_state=42,
    eval_metric="logloss",
    n_jobs=-1
)

# -----------------------------
# 9. Complete pipeline
# -----------------------------

pipeline = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        ("model", model)
    ]
)

# -----------------------------
# 10. Train/test split
# -----------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print("Training records:", len(X_train))
print("Testing records:", len(X_test))

# -----------------------------
# 11. TRAIN MODEL
# -----------------------------

print("\nTraining XGBoost...")

pipeline.fit(X_train, y_train)

print("Training completed!")

# -----------------------------
# 12. Predictions
# -----------------------------

predictions = pipeline.predict(X_test)

probabilities = pipeline.predict_proba(X_test)[:, 1]

# -----------------------------
# 13. Evaluation
# -----------------------------

print("\nMODEL RESULTS")

print("Accuracy:",
      accuracy_score(y_test, predictions))

print("Precision:",
      precision_score(y_test, predictions))

print("Recall:",
      recall_score(y_test, predictions))

print("F1 Score:",
      f1_score(y_test, predictions))

print("ROC-AUC:",
      roc_auc_score(y_test, probabilities))

print("\nConfusion Matrix:")

print(confusion_matrix(y_test, predictions))
print("\nTHRESHOLD TEST")

for threshold in [0.5, 0.4, 0.3, 0.2]:

    threshold_predictions = (
        probabilities >= threshold
    ).astype(int)

    print("\nThreshold:", threshold)

    print(
        "Precision:",
        precision_score(y_test, threshold_predictions)
    )

    print(
        "Recall:",
        recall_score(y_test, threshold_predictions)
    )

    print(
        "F1:",
        f1_score(y_test, threshold_predictions)
    )

    print("Confusion Matrix:")

    print(
        confusion_matrix(
            y_test,
            threshold_predictions
        )
    )