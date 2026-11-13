"""Compare a small fixed candidate set at the original validation false-alert budget."""
import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

from procurement_history import CATEGORICAL
from validation_recall import load_development, operating_point, select_false_alert_budget


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('dataset/procurement.csv'))
    parser.add_argument('--model', type=Path, default=Path('models/delivery_risk_model_clean.pkl'))
    parser.add_argument('--validation-start', required=True)
    parser.add_argument('--test-start', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Use a new output directory to preserve previous evidence.')
    train, validation = load_development(args.data, args.validation_start, args.test_start)
    original = joblib.load(args.model)
    columns = list(original.feature_names_in_)
    y_train, labels = train.late_delivery.astype(int), validation.late_delivery.astype(int).to_numpy()
    original.named_steps['model'].n_jobs = 1
    baseline_scores = original.predict_proba(validation[columns])[:, list(original.classes_).index(1)]
    baseline = operating_point(labels, baseline_scores, .5)
    budget = baseline['false_positives']
    numeric = [name for name in columns if name not in CATEGORICAL]
    histogram = Pipeline([
        ('preprocessor', ColumnTransformer([
            ('categorical', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=np.nan), CATEGORICAL),
            ('numeric', 'passthrough', numeric)])),
        ('model', HistGradientBoostingClassifier(max_iter=300, learning_rate=.05, max_leaf_nodes=31,
            l2_regularization=1, categorical_features=list(range(len(CATEGORICAL))),
            class_weight='balanced', early_stopping=False, random_state=42))])
    candidates = [
        ('original', original),
        ('forest_leaf_100', clone(original).set_params(model__min_samples_leaf=100, model__n_jobs=-1)),
        ('extra_trees', Pipeline([('preprocessor', clone(original.named_steps['preprocessor'])),
            ('model', ExtraTreesClassifier(n_estimators=300, min_samples_leaf=5,
                class_weight='balanced', random_state=42, n_jobs=-1))])),
        ('histogram_boosting', histogram)]
    results, best_key = [], None
    for name, model in candidates:
        if name != 'original':
            model.fit(train[columns], y_train)
        if 'n_jobs' in model.named_steps['model'].get_params():
            model.named_steps['model'].n_jobs = 1
        scores = model.predict_proba(validation[columns])[:, list(model.classes_).index(1)]
        point = select_false_alert_budget(labels, scores, budget)
        if name == 'original' and (point['true_positives'], point['false_positives']) == (baseline['true_positives'], baseline['false_positives']):
            point = baseline
        assert point['false_positives'] <= budget
        tradeoff = {str(limit): select_false_alert_budget(labels, scores, limit) for limit in (0, 16, 32, 64)}
        result = dict(candidate=name, selected=point, false_alert_budget_curve=tradeoff)
        results.append(result)
        # Strict improvement only; equal counts keep the earlier, simpler candidate.
        key = (point['true_positives'], -point['false_positives'])
        if best_key is None or key > best_key:
            best_key, best_name, best_model, best_scores, best_point = key, name, model, scores, point
        print(json.dumps(result), flush=True)
    args.output.mkdir(parents=True)
    improved = best_key > (baseline['true_positives'], -baseline['false_positives'])
    model_path = args.output / 'selected-model.pkl' if improved else args.model
    if improved:
        joblib.dump(best_model, model_path, compress=3)
    reloaded = joblib.load(model_path)
    scores = reloaded.predict_proba(validation[columns])[:, list(reloaded.classes_).index(1)]
    np.testing.assert_allclose(scores, best_scores, atol=1e-14, rtol=0)
    np.testing.assert_array_equal(scores >= best_point['threshold'], best_scores >= best_point['threshold'])
    report = dict(objective='Maximum validation true positives with false positives <= original model at threshold 0.50',
        candidate=best_name, false_alert_budget=budget, baseline=baseline, selected=best_point,
        improved_operating_point=improved, new_model_saved=improved,
        threshold=best_point['threshold'], positive_class=1,
        decision_rule='predict_proba(X)[:, positive_class_index] >= threshold; ordinary predict() uses 0.50',
        validation_start=args.validation_start, test_start=args.test_start,
        training_rows=len(train), validation_rows=len(validation), final_test_scored=False,
        source_model_sha256=hashlib.sha256(args.model.read_bytes()).hexdigest(),
        selected_model_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),
        data_sha256=hashlib.sha256(args.data.read_bytes()).hexdigest(),
        reload_scores_and_decisions_match=True, candidates=results,
        warning='Validation-selected synthetic results; repeated validation reuse can overfit selection. No independent improvement claim.')
    (args.output / 'policy.json').write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
