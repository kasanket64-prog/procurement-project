# Buyer pilot: delivery-delay evidence collection

This pack targets goods purchase-order lines for one consenting buyer. It
contains blank templates, not buyer records, consent or real-world model
validation. Copy the workbook outside this repository before filling it.

## Agree the pilot before collecting records

Record an authorized sponsor's approval reference, a purchasing data owner and a
receiving reviewer. Agree purpose, allowed fields, access roles, storage location,
expiry, retention/deletion date and withdrawal procedure in Pilot setup. Approval
is pending until the buyer confirms it. This operational checklist is not a
signed agreement or proof of rights. No outreach or data transfer is authorized
by preparing this pack.

Start with one site and product family with traceable PO and receipt records.
Include successful, late, partial, open and cancelled orders, not only problem
suppliers. Freeze the prediction moment: **at PO-line release/placement**. A later daily-monitoring model needs a separate experiment and
separate decision snapshots.

## Proposed target for buyer approval

Predict whether the **full original ordered quantity is accepted at the agreed
destination by the original documented supplier-committed promise date**, in the destination's IANA
timezone. Freeze original quantity, unit and promise. Append revisions; never
rewrite the original target to make a delay disappear. Agree grace period,
returns/rejections and material scope-change exclusions before labelling.
Do not assume any grace period or conversion rule from the blank template.

Start with a date-based target when the source states only dates. Do not invent
a time-of-day promise. An exact-time target requires a new approved definition.

Outcomes are reviewed labels, never predictor inputs:

- **on_time:** reconciled receipts show full original quantity accepted by deadline.
- **late:** full acceptance happened after deadline; or deadline passed and a
  reviewer verified complete receipt coverage through deadline without full
  acceptance. The latter can still be an open order; retain delivery_status.
- **pending/unknown:** deadline is not reached, evidence conflicts or coverage
  is incomplete. An open order is never automatically labelled on time.
- **cancelled/excluded:** preserve reason and timing. Do not silently classify
  cancellations or material specification/quantity changes as successful delivery.

Outcome known_at must be the earliest evidenced availability of the reviewed
result, at least as late as every source fact used. reviewed_at is the actual
review time. Never backdate either to placement or delivery. Preserve all open
orders and check label maturity at each future training/evaluation cutoff.

## Fields and priorities

| Table | Minimum practical capture | Purpose |
|---|---|---|
| Order snapshots | Stable line, supplier, product and destination IDs; release decision/placement times; original promise; quantity/unit; timezone; source/availability | Reconstruct the original decision. Collect price/currency, business unit, payment terms and contract status where sourced. |
| Promise events | Each original/revised promise, version, event time, known time and source | Preserve commitments without overwriting history. Post-release revisions are not release-time predictors. |
| Receipts | Every accepted/rejected/reversed quantity, unit, event and known time, source and linked receipt | Reconcile partial deliveries and completion. Historical receipts become features only after disclosure. |
| Signals | Sourced acknowledgement, stock/capacity commitment, shipment milestone, route disruption or scope change | Cancellation and material quantity/specification changes require event rows when they occur. Other enrichment is optional. Only facts known at decision time can be predictors. |
| Outcomes | Delivery status, label, completion if known, receipt-register coverage, reviewer and sources | Preserve mature ground truth separately from predictors. |

Every record also needs pilot_id, data_kind, source_ref, known_at, captured_at and
reviewer_id. Blank is missing; genuine zero is zero. First fix PO/receipt joins,
timestamps and quantity reconciliation. Then capture acknowledgements or stock
commitments the buyer already receives. Add capacity/disruption evidence only
where documented; unknown capacity is not zero capacity.

Never include current-order completion/delay, post-delivery quality rejection,
later-written delay explanations, later promises, final ERP status backfilled
as an earlier fact, or PO sequence patterns as decision-time evidence. Do not
invent measurements to fill optional columns.

## Preserve three different times

1. event_at / received_at / order_placed_at: when the event happened.
2. known_at: earliest source-supported time the buyer could use the fact.
3. captured_at: when this project copied or entered it.

At decision_at use only facts with known_at <= decision_at. If timestamps have
only day precision, use the conservative before-day rule unless within-day
ordering is evidenced. A future promise is valid if its communication was known
at the decision; its promised date need not precede the decision.

Store offset-aware ISO timestamps as text to preserve offsets, dates as
YYYY-MM-DD and timezone as an IANA name. Do not guess zones, invent midnight or
equate completion with disclosure when posting was delayed. Quarantine missing
availability evidence; distinguish unknown history from no previous orders.

An Order snapshot is immutable. Its known_at is the latest availability of its
populated decision-time business facts, supported by source_ref. Later project
capture/review metadata is not a predictor and is not part of that maximum. A field learned later
belongs in a timestamped Signal/Promise event, not backfilled into the original
snapshot. retrospective_unverified snapshots are not eligible for training yet.
For this first experiment, decision_at equals order_placed_at. A buyer-requested
needed-by date is not a supplier commitment. If the first supplier promise is
received only after release, do not backfill it as an order-time predictor;
exclude that line from this initial committed-promise experiment or agree a
separate acknowledgement-time decision definition before collection.

Append corrections with new IDs and supersedes_id/reverses_event_id; preserve
original evidence. For Order snapshots, leave supersedes_id blank on the first
snapshot and require it on each transcription correction, referencing the prior
snapshot_id for the same pilot_id and order_line_id. Keep the original decision
and source-supported fact availability, and record the actual correction capture
time. A later supplier promise is a Promise event, not a snapshot correction.
Before analysis, resolve one active snapshot per line: the unique end of a
reviewed correction chain. Missing links, cycles, multiple roots or competing
corrections remain quarantined until reviewed; never choose the last CSV row by
position or count all versions as orders.

Receipt quantities are positive: accepted adds quantity,
rejected adds no accepted quantity, and each uniquely identified reversal is
applied once against a referenced accepted receipt. Multiple partial reversals
are allowed only while their cumulative quantity does not exceed that acceptance.
Match line, destination and unit before sums. Resolve corrections and
scope changes explicitly; never delete inconvenient receipt rows.

For each cancellation or material quantity/specification change, require a
Signals row using cancellation, quantity_change or specification_change, with
event_at, known_at, captured_at, source_ref, reviewer_id and the documented reason
or change value. Also link that signal_id from Outcomes.exclusion_or_dispute.
If event timing is unavailable, preserve the source in quarantine and leave the
exclusion unresolved; do not fabricate a time from the review date. These events
are outcome/context after release and cannot enter earlier decision features.

Before labelling, the buyer must approve an explicit cancellation policy in
Pilot setup.grace_and_scope_rules for events before versus after the original
deadline (including any approved grace). Proposed policy: a cancellation before
the deadline is retained as cancelled/excluded, never on_time; after the deadline,
preserve any late result already evidenced by complete receipt coverage through
the deadline, with delivery_status=cancelled and label=late. If lateness cannot
be established, keep the outcome unknown pending evidence. Record any approved
deviation and exclusion count; do not silently remove overdue failures. Material
scope changes likewise require the agreed rule and original target to be kept.

## Practical first six weeks

| When | Buyer action | Project action / exit evidence |
|---|---|---|
| Week 1 | Sponsor approves scope and access; purchasing/receiving approve target and review budget | Walk one line from placement to receipt, including a revision/late posting where available. Complete Pilot setup and source mapping. |
| Week 2 | Export all available lines/history in scope plus receipt/revision logs | Reconcile about 20–30 varied lines as an ingestion dry run, resolving or quarantining exceptions. This count tests mechanics, not ML validity. |
| Weeks 3–4 | Capture new releases, changes, partials and cancellations | Freeze snapshots and review missingness/coverage weekly with the buyer. |
| Weeks 5–6 | Review outcomes and practical alert-review burden | Assess event count, timestamp coverage, product/supplier diversity and missingness; write a go/no-go decision. Continue following open lines until mature. |

Request the complete available history in scope (often 6–12 months if available),
including open and cancelled lines, and record omissions. There is no universal
minimum training sample or automatic six-week training gate. Long-lead orders
may require much longer follow-up.

Prefer ERP/CSV exports. Propose a short daily release/change check and a weekly
purchasing/receiving reconciliation, then agree the actual time burden with the
buyer. Do not create manual capacity estimates merely to increase feature count.

## Keep real and synthetic evidence separate

Use buyer-approved protected storage **outside Git**:

```text
<approved storage>/<pilot_id>/
  real/raw/        original restricted exports and documents
  real/working/    filled workbook and append-only event exports
  real/reviewed/   reconciled records and versioned review notes
  quarantine/     conflicting, unauthorized, unverified or undated records
  synthetic/      separately generated software-test fixtures only
  identity-key/   restricted pseudonym-to-identity mapping
```

Never mix synthetic fixtures into real training, evaluation or buyer-performance
reports. Each record carries data_kind. Declare real only for reviewed genuine
records within approved use; unverified is not real evidence. A declaration does
not authenticate a document. This workbook has no sample data and does not
default permission to approved or rows to real.

The repository holds only blank templates and guidance. Local
real-pilot/buyer-records/ and buyer-private/ paths are ignored as a fallback;
ignore rules do not provide access control or encryption. Never fill the tracked
blank template. Keep legal names, contacts, bank data and the identity key out of
shared analysis. Use protected source references, not public share links or
embedded document contents.

Limit access to approved roles. Preserve export hashes/revisions, buyer-approved
backups and a restore test, and follow agreed withdrawal/expiry/deletion steps.
No cloud/model-service uploads, redistribution or supplier contact without
separate approval. Purchasing decisions remain with the buyer.

## Weekly quality review and model gates

- Reconcile distinct lines and quantities with the source export; resolve duplicate
  IDs, multiple snapshots and revisions before generating a modelling row.
- Check event, known, capture and decision times against sources. A late entry
  must not change when the buyer first knew a fact.
- Reconcile partials/reversals by line, unit and destination. Do not invent FX,
  pack conversions, capacity or missing promises. Preserve scope changes.
- Review open/cancelled lines and receipt-register coverage explicitly. Unknown
  outcomes stay unknown; absence of a receipt is not proof without coverage.
- Trace disputed labels to the original promise and receipts, preserving reviewer,
  review time and unresolved questions.

Before modelling, freeze target version, decision use, exclusions and acceptable
weekly alert burden/precision–recall trade-off. Choose chronological cutoffs with
mature labels, reconstruct features as of each decision and keep genuinely future
evaluation closed. Compare operational baselines and report uncertainty,
calibration, missingness and new-supplier behavior. Run alongside existing work.

This pack does not import directly into the current trainer or quotation JSON
engine. A reviewed mapping/validation step is needed first. No real records were
collected, consent granted, messages sent or real-world performance established
by creating these templates.
