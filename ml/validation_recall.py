"""Select a recall-oriented threshold without scoring any final-test orders."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_recall_curve

from procurement_history import build_features


def load_development(path, validation_start, test_start):
    """Discard test rows before parsing their outcomes or building history."""
    start, end = pd.Timestamp(validation_start), pd.Timestamp(test_start)
    if any(pd.isna(day) or day.tzinfo is not None or day != day.normalize() for day in (start, end)) or start >= end:
        raise ValueError('Require calendar dates with validation_start < test_start.')
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        rows = [row for row in csv.DictReader(stream) if pd.Timestamp(row['order_date']) < end]
    if not rows:
        raise ValueError('No pre-test orders available.')
    features = build_features(pd.DataFrame(rows))
    validation = features[(features.order_date >= start) & (features.outcome_available_at < end)
                          & features.late_delivery.notna()].copy()
    if validation.empty:
        raise ValueError('No mature validation outcomes available.')
    train = features[(features.order_date < start) & (features.outcome_available_at < start)
                     & features.late_delivery.notna()].copy()
    if train.empty:
        raise ValueError('No mature training outcomes available.')
    return train, validation


def load_validation(path, validation_start, test_start):
    return load_development(path, validation_start, test_start)[1]


def threshold_tradeoff(labels, probabilities):
    labels, probabilities = np.asarray(labels), np.asarray(probabilities)
    if (labels.ndim != 1 or probabilities.shape != labels.shape or set(labels) != {0, 1}
            or not np.isfinite(probabilities).all() or ((probabilities < 0) | (probabilities > 1)).any()):
        raise ValueError('Require both binary outcome classes and finite probabilities in [0, 1].')
    precision, recall, thresholds = precision_recall_curve(labels, probabilities)
    precision, recall = precision[:-1], recall[:-1]
    denominator = 4 * precision + recall
    f2 = np.divide(5 * precision * recall, denominator, out=np.zeros_like(precision), where=denominator > 0)
    return pd.DataFrame(dict(threshold=thresholds, precision=precision, recall=recall, f2=f2))


def operating_point(labels, probabilities, threshold):
    tn, fp, fn, tp = confusion_matrix(labels, probabilities >= threshold, labels=[0, 1]).ravel()
    precision, recall = tp / (tp + fp) if tp + fp else 0, tp / (tp + fn)
    return dict(threshold=float(threshold), precision=float(precision), recall=float(recall),
                f2=float(5 * tp / (5 * tp + 4 * fn + fp)),
                true_positives=int(tp), false_positives=int(fp), false_negatives=int(fn),
                true_negatives=int(tn), alerts=int(tp + fp))


def select_precision_constrained(curve):
    """Provisional review budget: at least one correct alert per false alert."""
    eligible = curve[curve.precision >= .5]
    if eligible.empty:
        raise ValueError('No validation threshold reaches 50% precision.')
    return eligible.sort_values(['recall', 'precision', 'threshold'], ascending=False).iloc[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('dataset/procurement.csv'))
    parser.add_argument('--model', type=Path, default=Path('models/delivery_risk_model_clean.pkl'))
    parser.add_argument('--validation-start', required=True)
    parser.add_argument('--test-start', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix('.csv').exists():
        raise FileExistsError('Use a new output filename to preserve previous evidence.')
    validation = load_validation(args.data, args.validation_start, args.test_start)
    model_hash = hashlib.sha256(args.model.read_bytes()).hexdigest()
    model = joblib.load(args.model)
    # Fixed tree order makes threshold boundary decisions reproducible across runs.
    model.named_steps['model'].n_jobs = 1
    scores = model.predict_proba(validation[list(model.feature_names_in_)])[:, list(model.classes_).index(1)]
    labels = validation.late_delivery.astype(int).to_numpy()
    curve = threshold_tradeoff(labels, scores)
    selected = curve.sort_values(['f2', 'precision', 'threshold'], ascending=False).iloc[0]
    points = {'baseline': operating_point(labels, scores, .5),
              'selected_max_f2': operating_point(labels, scores, selected.threshold)}
    for floor in (.9, .75, .5):
        eligible = curve[curve.precision >= floor].sort_values(['recall', 'precision', 'threshold'], ascending=False)
        if not eligible.empty:
            points[f'precision_at_least_{floor}'] = operating_point(labels, scores, eligible.iloc[0].threshold)
    for threshold in (.2, .15, .1):
        points[f'fixed_{threshold}'] = operating_point(labels, scores, threshold)
    late_scores = scores[labels == 1]
    fn = (labels == 1) & (scores < .5)
    groups = []
    for category, indices in validation.groupby('category').indices.items():
        indices = np.asarray(indices)
        actual = labels[indices] == 1
        groups.append(dict(category=category, late_orders=int(actual.sum()),
                           missed_at_half=int(fn[indices].sum()),
                           missed_at_selected=int(((scores[indices] < selected.threshold) & actual).sum())))
    report = dict(model_sha256=model_hash, data_sha256=hashlib.sha256(args.data.read_bytes()).hexdigest(),
                  validation_start=args.validation_start, test_start=args.test_start,
                  validation_rows=len(labels), late_orders=int(labels.sum()),
                  objective='Maximum validation F2; ties prefer precision then higher threshold',
                  score_rule='late if score >= selected threshold; probabilities unchanged',
                  final_test_scored=False, points=points,
                  late_score_quantiles={str(q): float(np.quantile(late_scores, q)) for q in (0, .1, .25, .5, .75, .9, 1)},
                  baseline_missed_by_score_band={f'{low}-{high}': int((fn & (scores >= low) & (scores < high)).sum())
                      for low, high in [(0, .1), (.1, .15), (.15, .2), (.2, .3), (.3, .5)]},
                  categories=groups,
                  warning='Validation-selected synthetic policy, not independently evaluated or approved for purchasing.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
    curve.to_csv(args.output.with_suffix('.csv'), index=False, mode='x')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
