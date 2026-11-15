"""Shared as-of feature definitions for evaluation and application inference."""
import numpy as np
import pandas as pd

CATEGORICAL = ['supplier_id', 'supplier_country', 'category', 'item', 'business_unit', 'payment_terms']
NUMERIC = ['unit_price', 'quantity', 'line_total', 'on_contract', 'promised_lead_days',
           'supplier_previous_orders', 'supplier_completed_orders', 'supplier_open_orders',
           'supplier_overdue_orders', 'supplier_late_rate', 'supplier_avg_delay',
           'order_month', 'order_dayofweek']
FEATURES = CATEGORICAL + NUMERIC
HISTORY = ['supplier_previous_orders', 'supplier_completed_orders', 'supplier_open_orders',
           'supplier_overdue_orders', 'supplier_completed_late', 'supplier_late_rate', 'supplier_avg_delay']

def build_features(raw):
    """Features at start of each order day; final outcomes are joined by availability."""
    d = raw.copy(deep=True)
    required = set(CATEGORICAL + ['po_id', 'order_date', 'promised_delivery_date',
                                'actual_delivery_date', 'unit_price', 'quantity', 'line_total', 'on_contract'])
    if required - set(d):
        raise ValueError(f'Missing source fields: {sorted(required - set(d))}')
    if d.po_id.isna().any() or d.po_id.duplicated().any():
        raise ValueError('Order IDs must be present and unique.')
    for col in ['order_date', 'promised_delivery_date', 'actual_delivery_date']:
        d[col] = pd.to_datetime(d[col], errors='raise').dt.normalize()
    if d[['order_date', 'promised_delivery_date']].isna().any().any():
        raise ValueError('Missing order/promise date.')
    if (d.promised_delivery_date < d.order_date).any() or (d.actual_delivery_date < d.order_date).any():
        raise ValueError('Promise/completion cannot precede order placement.')
    if d[CATEGORICAL].isna().any().any():
        raise ValueError('Missing categorical order information.')
    for col in ['unit_price', 'quantity', 'line_total']:
        d[col] = pd.to_numeric(d[col], errors='raise')
        if not np.isfinite(d[col]).all() or (d[col] <= 0).any():
            raise ValueError(f'{col} must be finite and positive.')
    if not np.allclose(d.line_total, d.unit_price * d.quantity, atol=.011, rtol=0):
        raise ValueError('Line totals are inconsistent with order-time price and quantity.')
    mapping = {'true': 1, 'false': 0, '1': 1, '0': 0}
    d['on_contract'] = d.on_contract.astype(str).str.lower().map(mapping)
    if d.on_contract.isna().any():
        raise ValueError('Invalid contract flag.')
    if 'outcome_available_at' in d:
        d['outcome_available_at'] = pd.to_datetime(d.outcome_available_at, errors='raise').dt.normalize()
    else:
        d['outcome_available_at'] = d.actual_delivery_date
    if ((d.outcome_available_at < d.actual_delivery_date)
            | (d.outcome_available_at.notna() & d.actual_delivery_date.isna())).any():
        raise ValueError('Outcome availability cannot precede actual completion.')
    d = d.sort_values(['order_date', 'po_id']).reset_index(drop=True)
    d['delivery_delay_days'] = (d.actual_delivery_date - d.promised_delivery_date).dt.days
    d['late_delivery'] = (d.delivery_delay_days > 0).astype(float).where(d.actual_delivery_date.notna())
    d['promised_lead_days'] = (d.promised_delivery_date - d.order_date).dt.days
    d['order_month'] = d.order_date.dt.month
    d['order_dayofweek'] = d.order_date.dt.day_of_week
    for col in HISTORY:
        d[col] = 0.0
    for _, group in d.groupby('supplier_id', sort=False):
        at = group.order_date.to_numpy()
        completed = group[group.outcome_available_at.notna()].sort_values(['outcome_available_at', 'po_id'])
        known = np.searchsorted(completed.outcome_available_at.to_numpy(), at, side='left')
        placed = np.searchsorted(np.sort(at), at, side='left')
        late_sum = np.r_[0., completed.late_delivery.cumsum().to_numpy()][known]
        delay_sum = np.r_[0., completed.delivery_delay_days.cumsum().to_numpy()][known]
        due = np.searchsorted(np.sort(group.promised_delivery_date.to_numpy()), at, side='left')
        # Subtract only completed orders whose promises are also before this day.
        closed_due_at = np.maximum(completed.outcome_available_at.to_numpy(), completed.promised_delivery_date.to_numpy())
        closed_due = np.searchsorted(np.sort(closed_due_at), at, side='left')
        values = [placed, known, placed - known, due - closed_due, late_sum,
                  np.divide(late_sum, known, out=np.zeros(len(group)), where=known > 0),
                  np.divide(delay_sum, known, out=np.zeros(len(group)), where=known > 0)]
        for col, value in zip(HISTORY, values):
            d.loc[group.index, col] = value
    if (d[['supplier_open_orders', 'supplier_overdue_orders']] < 0).any().any():
        raise AssertionError('Invalid history counts.')
    if not np.isfinite(d[NUMERIC].to_numpy()).all():
        raise ValueError('Nonfinite feature value.')
    return d
