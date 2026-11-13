"""Compare two leaf-size changes using training and validation orders only."""
import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.base import clone

from validation_recall import load_development, operating_point, select_precision_constrained, threshold_tradeoff


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('dataset/procurement.csv'))
    parser.add_argument('--model', type=Path, default=Path('models/delivery_risk_model_clean.pkl'))
    parser.add_argument('--validation-start', required=True)
    parser.add_argument('--test-start', required=True)
    parser.add_argument('--output', type=Path, required=True, help='New directory for the policy, model and comparisons')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Use a new output directory to preserve previous evidence.')
    train, validation = load_development(args.data, args.validation_start, args.test_start)
    original = joblib.load(args.model)
    columns = list(original.feature_names_in_)
    labels = validation.late_delivery.astype(int).to_numpy()
    results, best, best_scores = [], None, None
    for leaf in (1, 20, 100):
        if leaf == 1:
            model = original
        else:
            model = clone(original).set_params(model__min_samples_leaf=leaf, model__n_jobs=-1)
            model.fit(train[columns], train.late_delivery.astype(int))
        model.named_steps['model'].n_jobs = 1
        scores = model.predict_proba(validation[columns])[:, list(model.classes_).index(1)]
        curve = threshold_tradeoff(labels, scores)
        chosen = select_precision_constrained(curve)
        point = operating_point(labels, scores, chosen.threshold)
        results.append(dict(min_samples_leaf=leaf, selected=point, fixed_half=operating_point(labels, scores, .5)))
        key = (point['recall'], point['precision'], -leaf)
        if best is None or key > best:
            best, best_scores, best_model, best_point, best_leaf = key, scores, model, point, leaf
        print(json.dumps(results[-1]), flush=True)
    args.output.mkdir(parents=True)
    path = args.output / 'selected-model.pkl'
    joblib.dump(best_model, path, compress=3)
    reloaded = joblib.load(path)
    reloaded_scores = reloaded.predict_proba(validation[columns])[:, list(reloaded.classes_).index(1)]
    np.testing.assert_allclose(reloaded_scores, best_scores, rtol=0, atol=1e-14)
    np.testing.assert_array_equal(reloaded_scores >= best_point['threshold'], best_scores >= best_point['threshold'])
    policy = dict(objective='Maximum validation recall subject to precision >= 0.50; ties prefer precision then smaller leaves',
                  precision_floor=.5, threshold=best_point['threshold'], positive_class=1,
                  rule='late alert if predict_proba(X)[:, positive_class_index] >= threshold; pipeline.predict retains 0.50',
                  min_samples_leaf=best_leaf, validation_start=args.validation_start, test_start=args.test_start,
                  training_rows=len(train), validation_rows=len(validation), final_test_scored=False,
                  source_model_sha256=hashlib.sha256(args.model.read_bytes()).hexdigest(),
                  selected_model_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  data_sha256=hashlib.sha256(args.data.read_bytes()).hexdigest(),
                  validation_operating_point=best_point, candidates=results,
                  reload_scores_and_decisions_match=True,
                  warning='Provisional synthetic review policy. Precision floor is an assumption, not a buyer-approved requirement.')
    (args.output / 'policy.json').write_text(json.dumps(policy, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
