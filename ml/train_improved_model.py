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


from argparse import ArgumentParser
from procurement_history import build_features
from procurement_training import chronological_split

parser = ArgumentParser(description='Train the synthetic demo with as-of history and mature chronological labels.')
parser.add_argument('--validation-start', required=True, help='First validation order day (YYYY-MM-DD)')
parser.add_argument('--test-start', required=True, help='First final-test order day (YYYY-MM-DD)')
parser.add_argument('--as-of', required=True, help='Exclusive final outcome-availability cutoff (YYYY-MM-DD)')
args = parser.parse_args()

df = build_features(pd.read_csv('dataset/procurement.csv'))
print('SYNTHETIC EXPERIMENT - not validated real supplier risk.')
print('Dataset shape:', df.shape)

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


train, validation, test = chronological_split(
    df, args.validation_start, args.test_start, args.as_of
)
X_train, y_train = train[features], train['late_delivery'].astype(int)
X_validation, y_validation = validation[features], validation['late_delivery'].astype(int)
X_test, y_test = test[features], test['late_delivery'].astype(int)
if y_train.nunique() != 2:
    raise ValueError('Training requires both on-time and late mature outcomes.')

for name, partition in [('Training', train), ('Validation', validation), ('Final test', test)]:
    print(name, len(partition), '| order days:', partition.order_date.min().date(),
          'to', partition.order_date.max().date(),
          '| latest available label:', partition.outcome_available_at.max().date())
print('Excluded immature/open/out-of-window rows:', len(df) - len(train) - len(validation) - len(test))
print('Threshold is fixed at 0.50 for final testing; other thresholds are validation diagnostics only.')

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
    "\nTraining with outcome-available history..."
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
    "FINAL CHRONOLOGICAL TEST RESULTS (fixed threshold 0.50)"
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
    roc_auc_score(y_test, probabilities) if y_test.nunique() == 2 else "Unavailable: only one test class"
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
# 19. VALIDATION THRESHOLD DIAGNOSTICS
# ==========================================

print(
    "\n=========================="
)

print(
    "VALIDATION THRESHOLD DIAGNOSTICS"
)

print(
    "=========================="
)


validation_probabilities = pipeline.predict_proba(X_validation)[:, 1]

thresholds = [
    0.50,
    0.40,
    0.30,
    0.20
]


for threshold in thresholds:

    threshold_predictions = (
        validation_probabilities >= threshold
    ).astype(int)

    print(
        "\nThreshold:",
        threshold
    )

    print(
        "Precision:",
        precision_score(
            y_validation,
            threshold_predictions,
            zero_division=0
        )
    )

    print(
        "Recall:",
        recall_score(
            y_validation,
            threshold_predictions
        )
    )

    print(
        "F1:",
        f1_score(
            y_validation,
            threshold_predictions
        )
    )

    print(
        confusion_matrix(
            y_validation,
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