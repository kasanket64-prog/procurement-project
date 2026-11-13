"""Chronological evaluation partitions for precomputed as-of order features."""
import pandas as pd


def chronological_split(features, validation_start, test_start, as_of):
    """Only use labels available strictly before each partition's scoring cutoff."""
    validation_start, test_start, as_of = [
        pd.Timestamp(value) for value in (validation_start, test_start, as_of)
    ]
    boundaries = (validation_start, test_start, as_of)
    if any(pd.isna(value) or value.tzinfo is not None or value != value.normalize()
           for value in boundaries):
        raise ValueError('Cutoffs must be timezone-free calendar dates.')
    if not validation_start < test_start < as_of:
        raise ValueError('Require validation_start < test_start < as_of.')
    placed = features.order_date
    available = features.outcome_available_at
    labeled = features.late_delivery.notna()
    train = features[(placed < validation_start) & (available < validation_start) & labeled].copy()
    validation = features[(placed >= validation_start) & (placed < test_start)
                          & (available < test_start) & labeled].copy()
    test = features[(placed >= test_start) & (placed < as_of)
                    & (available < as_of) & labeled].copy()
    for name, partition in [('training', train), ('validation', validation), ('test', test)]:
        if partition.empty:
            raise ValueError(f'No mature labeled orders in the {name} partition.')
    return train, validation, test
