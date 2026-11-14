# Reconcile supplied receipt events

This read-only command checks receipt quantities against each validated active
order snapshot. It uses the existing CSV schemas and snapshot approval checks.
No workbook changes, new dependencies or model training are required.

## Input and command

Keep these three working CSVs in the buyer-approved protected folder outside Git:
`pilot_setup.csv`, `order_snapshots.csv` and `receipt_events.csv`. Keep the tracked
templates blank. Complete approval/source review before processing genuine records.
Export the existing workbook tables to the exact CSV headers if needed; this
command does not read Excel files directly.

```powershell
python ml/buyer_receipts.py "C:\BuyerApprovedStorage\pilot-working"
```

Use the actual approved location, not the illustrative path. Output is JSON in
the terminal; no files are created or modified, and no network calls are made.
Exit code 0 means the supplied ledger reconciled; code 2 means a batch is blocked
with a field/relationship error. A missing receipt file blocks processing. A
header-only receipt file is accepted as explicitly supplying no events, not as
proof that the buyer's register is complete.

Output contains pseudonymous order-line IDs and per-line quantities. Treat it as
buyer information when using real inputs; do not copy it into GitHub. It omits
source references, reviewer identities and business documents. No real buyer
records or completed example files are included in this repository.

## Quantity rules

- Accepted adds a strictly positive quantity. Rejected is reported separately
  and adds nothing to accepted balance. Rejected-only lines are `not_accepted`.
- Reversal subtracts a positive quantity from an existing accepted receipt on
  the same pilot/line/destination/unit. It cannot target a rejection/reversal,
  precede the acceptance or precede its buyer-known time. Only reversal rows may
  populate `reverses_event_id`.
- Receipt IDs are unique. Several partial reversals may reference one acceptance,
  but their combined quantity cannot exceed it. Every uniquely identified event
  is applied once; source-level duplicate submissions still require human review.
- Line, destination and unit must match the active original snapshot exactly.
  There are no implicit unit/pack conversions or sums across different units.
  Quantities use exact decimal arithmetic, never binary floating-point totals.
- Receipt times must satisfy `placement <= event_at <= known_at <= captured_at
  <= check time`; capture is within the current approval window. Unverified,
  synthetic, future or mismatched records block the batch rather than disappearing.

For each line the report shows ordered, gross accepted, rejected, reversed,
net accepted, remaining and over-accepted quantities. Net is accepted minus
reversals; remaining never goes below zero. Excess is retained and flagged with
`needs_quantity_review` rather than silently capped or treated as a scope change.
`receipt_status` is `no_receipts`, `not_accepted`, `partial` or `quantity_met`.
These are supplied-ledger states, not independently verified delivery statuses.

Events are evaluated in actual event-time order, independent of CSV ordering.
Same-instant events are combined before testing the original quantity threshold.
If a reversal drops the balance below that threshold, completion is cleared;
later acceptance can establish a new `ledger_complete_at`. Reversals that leave
enough accepted quantity do not move that timestamp. The derived timestamp is
the latest threshold crossing still valid in the supplied event ledger, not a
reviewed receipt date or label. Buyer-approved return/correction policy is still
needed to interpret it operationally.

## Remaining review

The report always says `coverage_confirmed: false`, `model_ready: false` and
`purchase_authorized: false`. The checker does not authenticate sources, establish
register completeness, inspect Promise/Signal/Outcome tables, apply cancellation
or material-change rules, choose grace periods or assign on-time/late labels.
Missing receipts cannot establish lateness without reviewed register coverage.
Subsequent outcome review and the modelling adapter remain separate work.

Run `python -m unittest discover -s tests -v` for the artificial-fixture tests.
They exercise partial/full acceptance, rejection, reversal caps and targets,
completion reset/restoration, simultaneous/reordered events, corrected snapshots,
unit/site joins, read-only I/O, blocked inputs and the existing snapshot controls.
Software tests do not validate an actual buyer's process or delivery performance.
