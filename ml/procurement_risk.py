"""Supplier-history baseline selected in Phase B; no forest inference or fitting."""
import math
import pandas as pd
from procurement_history import build_features

TRAIN_START = pd.Timestamp('2023-01-01')
TRAIN_END = pd.Timestamp('2025-01-01')
PRIOR_AVAILABLE_AT = pd.Timestamp('2025-04-01')
PSEUDO_ORDERS = 10


class SupplierHistoryRisk:
    """An immutable-by-convention, day-specific snapshot shared by all scenarios.

    Rates are supplier-wide, not product-specific. Quantity, price and promises
    cannot change a supplier's already observed delivery outcomes.
    """
    method = 'Supplier history (smoothed; synthetic)'

    def __init__(self, raw, today, *, prior=None, prior_available_at=PRIOR_AVAILABLE_AT):
        self.as_of = pd.Timestamp(today).tz_localize(None).normalize()
        if self.as_of < pd.Timestamp(prior_available_at):
            raise ValueError('Decision date precedes availability of the baseline prior.')
        built = build_features(raw)
        if prior is None:
            training = built[(built.order_date >= TRAIN_START) & (built.order_date < TRAIN_END)]
            if training.empty or training.outcome_available_at.isna().any() or (
                    training.outcome_available_at >= PRIOR_AVAILABLE_AT).any():
                raise ValueError('The fixed Phase B training prior cannot be established from mature source outcomes.')
            prior = float(training.late_delivery.mean())
            self.prior_orders = len(training)
        else:
            self.prior_orders = None
        if not math.isfinite(prior) or not 0 <= prior <= 1:
            raise ValueError('Prior must be a finite rate between zero and one.')
        self.prior = prior
        self.options = {field: sorted(built.loc[built.order_date < self.as_of, field].unique().tolist())
                        for field in ('business_unit', 'payment_terms')}
        observed = built[built.order_date < self.as_of]
        self.last_order_date = None if observed.empty else str(observed.order_date.max().date())
        known = observed[observed.outcome_available_at < self.as_of]
        self.last_outcome_date = None if known.empty else str(known.outcome_available_at.max().date())
        # Query rows use the SAME builder as evaluation, not a second aggregation.
        queries = observed.drop_duplicates('supplier_id').copy()
        ids = [f'__risk_snapshot__{i}' for i in range(len(queries))]
        if set(ids).intersection(built.po_id):
            raise ValueError('Reserved risk-snapshot order ID in source data.')
        queries['po_id'] = ids
        queries['order_date'] = self.as_of
        queries['promised_delivery_date'] = self.as_of
        queries['actual_delivery_date'] = pd.NaT
        queries['outcome_available_at'] = pd.NaT
        if queries.empty:
            self.history = pd.DataFrame(columns=['supplier_id'])
        else:
            combined = pd.concat([built, queries], ignore_index=True)
            features = build_features(combined)
            self.history = features[features.po_id.isin(ids)].copy().reset_index(drop=True)

    def evidence(self, supplier_id, today):
        if pd.Timestamp(today).tz_localize(None).normalize() != self.as_of:
            raise ValueError('Risk snapshot date differs from the decision date; rebuild the snapshot.')
        rows = self.history[self.history.supplier_id == supplier_id]
        row = rows.iloc[0] if not rows.empty else None
        completed = int(row.supplier_completed_orders) if row is not None else 0
        late = int(row.supplier_completed_late) if row is not None else 0
        status = ('Prior only: no known completed supplier orders' if completed == 0
                  else 'Limited supplier history' if completed < 20 else 'Established supplier history')
        return {
            'risk_method': self.method,
            'risk_completed_orders': completed,
            'risk_late_orders': late,
            'risk_open_orders': int(row.supplier_open_orders) if row is not None else 0,
            'risk_overdue_orders': int(row.supplier_overdue_orders) if row is not None else 0,
            'risk_evidence': status,
            'risk_as_of': str(self.as_of.date()),
            'risk_prior_only': completed == 0,
            'risk_estimate': 100 * (late + PSEUDO_ORDERS * self.prior) / (completed + PSEUDO_ORDERS),
        }

    def supplier_risk(self, supplier_id, today):
        return self.evidence(supplier_id, today)['risk_estimate']
