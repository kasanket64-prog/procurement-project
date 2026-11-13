"""Experimental order-time signals; the existing production feature schema stays unchanged."""
import numpy as np

from procurement_history import build_features

WORKLOAD = ['supplier_completed_orders', 'supplier_open_orders', 'supplier_overdue_orders',
            'supplier_open_share', 'supplier_overdue_share']
RECENT = ['supplier_completed_30d', 'supplier_late_rate_30d', 'supplier_completed_90d',
          'supplier_late_rate_90d', 'supplier_avg_delay_90d']
ITEM = ['item_previous_orders', 'item_completed_orders', 'item_late_rate', 'item_avg_delay',
        'quantity_vs_item_history', 'price_vs_item_history', 'lead_vs_item_history']
EXTRA = WORKLOAD + RECENT + ITEM


def build_experiment_features(raw):
    d = build_features(raw)
    d['supplier_open_share'] = np.divide(d.supplier_open_orders, d.supplier_previous_orders,
        out=np.zeros(len(d)), where=d.supplier_previous_orders > 0)
    d['supplier_overdue_share'] = np.divide(d.supplier_overdue_orders, d.supplier_open_orders,
        out=np.zeros(len(d)), where=d.supplier_open_orders > 0)
    for column in RECENT + ITEM:
        d[column] = 0.0
    for _, group in d.groupby('supplier_id', sort=False):
        at = group.order_date.to_numpy()
        known = group[group.outcome_available_at.notna()].sort_values(['outcome_available_at', 'po_id'])
        available = known.outcome_available_at.to_numpy()
        end = np.searchsorted(available, at, side='left')
        late_sum = np.r_[0., known.late_delivery.cumsum().to_numpy()]
        delay_sum = np.r_[0., known.delivery_delay_days.cumsum().to_numpy()]
        for days in (30, 90):
            start = np.searchsorted(available, at - np.timedelta64(days, 'D'), side='left')
            count = end - start
            d.loc[group.index, f'supplier_completed_{days}d'] = count
            d.loc[group.index, f'supplier_late_rate_{days}d'] = np.divide(
                late_sum[end] - late_sum[start], count, out=np.zeros(len(group)), where=count > 0)
            if days == 90:
                d.loc[group.index, 'supplier_avg_delay_90d'] = np.divide(
                    delay_sum[end] - delay_sum[start], count, out=np.zeros(len(group)), where=count > 0)
    for _, group in d.groupby(['supplier_id', 'item'], sort=False):
        at = group.order_date.to_numpy()
        known = group[group.outcome_available_at.notna()].sort_values(['outcome_available_at', 'po_id'])
        count = np.searchsorted(known.outcome_available_at.to_numpy(), at, side='left')
        d.loc[group.index, 'item_completed_orders'] = count
        for target, source in [('item_late_rate', 'late_delivery'), ('item_avg_delay', 'delivery_delay_days')]:
            total = np.r_[0., known[source].cumsum().to_numpy()][count]
            d.loc[group.index, target] = np.divide(total, count, out=np.zeros(len(group)), where=count > 0)
        # The base builder sorts by placement day; same-day placements are excluded together.
        placed = np.searchsorted(at, at, side='left')
        d.loc[group.index, 'item_previous_orders'] = placed
        for target, source in [('quantity_vs_item_history', 'quantity'),
                               ('price_vs_item_history', 'unit_price'), ('lead_vs_item_history', 'promised_lead_days')]:
            total = np.r_[0., group[source].cumsum().to_numpy()][placed]
            mean = np.divide(total, placed, out=np.zeros(len(group)), where=placed > 0)
            d.loc[group.index, target] = np.divide(group[source].to_numpy(), mean,
                out=np.ones(len(group)), where=mean > 0)
    if not np.isfinite(d[EXTRA].to_numpy()).all():
        raise ValueError('Nonfinite experimental feature value.')
    return d
