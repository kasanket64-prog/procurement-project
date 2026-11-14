# Small buyer delivery pilot — ready for buyer review

Status: preparation only. No buyer has been enrolled, no approval has been granted, and no actual business records are included. Use the existing `buyer-data-template.xlsx`, its CSV alternatives and `field-dictionary.csv`; no new data format or model is required.

## Proposed scope

One consenting buyer, one receiving site and one product family. Start with a 20–30-line historical dry run and then record every newly released line in the agreed scope for four weeks. Reconcile weekly and review progress around week six; follow open orders until their outcomes are evidenced even if that takes longer. Counts and weeks test the collection process, not model readiness.

Historical lines should come from a defined consecutive date window or a documented source-export rule, not a hand-picked set of delays. Include on-time, late, partial, open and canceled lines. If needed, separately inspect additional edge cases for process testing; do not mix that deliberately selected sample into performance estimates. Agree the available historical window and omissions with the buyer.

Use old and new records from the **same buyer**, retaining their collection group. Do not append DataCo records or synthetic fixtures. Stable line IDs prevent a historical order still open at pilot start from being counted again as a new order.

## Before recording buyer data

The sponsor/data owner completes `Pilot setup` (or `csv-templates/pilot_setup.csv`) and confirms approved use, source access, receiving reviewer, one-site/product scope, timezone, storage, retention, withdrawal and permitted access. Leave permission pending until approval is evidenced. Preparing this document or downloading the blank workbook is not consent, outreach or authorization to upload records elsewhere.

Agree these existing setup fields in particular:

| Setup field | Decision to record |
|---|---|
| history_window | Historical dates/export rule, omissions, prospective start and proposed end |
| decision_rule | PO-line release/placement; `decision_at = order_placed_at` |
| target_version | Full original quantity accepted at the original destination by the original supplier-committed date |
| grace_and_scope_rules | Explicit grace, cancellation, returns/rejections, reversals and material-change treatment |
| timezone | Destination IANA timezone; date-based promise unless an exact-time target is separately agreed |
| permitted_use | Collection/reconciliation first; model development only if included in approved scope |

## Use the existing template

Copy the blank workbook **outside Git** into buyer-approved protected storage before filling it. Alternatively use the existing CSV templates; choose one authoritative working record, rather than maintaining contradictory workbook and CSV copies. No credentials, bank details or personal contacts belong in the shared analysis.

1. **Order snapshots:** one immutable release snapshot per line. Record stable pseudonymous line/supplier/product/destination IDs, placement/decision times, original supplier promise, promise evidence, original quantity/unit and destination timezone. Complete provenance/verification fields; optional commercial facts stay blank if not sourced.
2. **Promise events:** record the original communication and each revision with its event time, buyer-known time, capture time and protected source reference. Never overwrite the original promise.
3. **Receipts:** append every accepted, rejected or reversed quantity, linked to the correct line, destination and unit. Record actual acceptance time separately from ERP posting/buyer-known time. Partial delivery is not full completion.
4. **Outcomes:** the receiving reviewer reconciles receipts and records delivery status, label, full accepted-completion time where established, coverage, review time and evidence-known time. This table is outcome evidence, never release-time input.
5. **Signals:** optional for this small pilot; collect only sourced facts already received by the buyer. Later events cannot be backfilled as release-time predictors.

For a historical reconstruction, `captured_at` is today's real extraction/entry time, not a fabricated historical timestamp. Use source-supported `known_at`; if release-time availability cannot be established, use `retrospective_unverified` for the snapshot and quarantine it from prediction experiments. Prospective snapshots also need evidence before they are marked `verified_as_of`. Set `data_kind` to real only after genuine source and approved-use checks, never by default.

If the supplier's first commitment arrived after release, preserve it in Promise events. Do not relabel the buyer's requested date as a supplier promise or backfill the later commitment. Keep the line as an exception outside this release-time committed-promise cohort unless a different decision point is agreed before the relevant collection/experiment.

## What counts as the actual delivery date?

For this pilot it is the date/time at which the full original quantity was **accepted at the agreed destination**, after reviewed receipt corrections. A supplier dispatch date, carrier estimate, invoice date or final ERP status alone does not establish acceptance.

| Evidence at review | Treatment |
|---|---|
| Full original quantity accepted by original deadline | `on_time`, with reconciled receipts |
| Full quantity accepted after original deadline | `late`; preserve actual completion and original promise |
| Deadline passed, not fully accepted, complete receipt coverage confirmed through deadline | `late` may be supported while delivery remains open/partial |
| Deadline not reached, missing promise/receipt coverage, or conflicting facts | `pending` or `unknown`; never assume on-time |
| Canceled order or material scope change | Preserve reason/time; use agreed cancellation/exclusion policy, never an automatic successful delivery |

Keep event time, earliest evidenced buyer-known time, capture time and review time distinct. Do not invent exact times for date-only source records. Resolve precision limitations before declaring a timestamp-required record eligible. The original promise remains the target even if a later revision is accepted commercially.

## Keep collection groups and data sources separate

Suggested protected layout, outside the repository:

```text
<buyer-approved storage>/<pilot_id>/
  real/raw/historical/
  real/raw/prospective/
  real/working/buyer-data-template.xlsx
  real/reviewed/
  quarantine/
  identity-key/
```

Use distinct protected export/source references for historical and prospective intake so each row's collection group remains traceable. A later receipt for an old open order stays attached to that same historical line. Corrections and subsequent events are appended, not counted as new orders. Keep synthetic fixtures in a separate test location and public DataCo data in its existing research collection. Do not merge any of those rows into buyer evidence.

The repository holds only blank templates, instructions and tests. Approved code/docs can later be proposed to main through review; actual records, filled workbooks, source documents and identity mappings do not belong in Git. Ignore rules are only an accidental-commit fallback, not protected storage.

## First weekly review and pilot exit

Purchasing verifies original promises/quantities and snapshot timing; receiving verifies receipts, partials, rejections, cancellations and coverage; the project owner reconciles source counts and logs exceptions. Agree the actual workload with those roles; a daily release/change check plus weekly reconciliation is a proposal, not an automated schedule.

At each review record total distinct lines by collection group, missing original promises, unverified availability, pending/unknown outcomes, cancellations, reconciled outcomes and unresolved joins/units. Report all exclusions and source coverage. Do not count a label as usable merely because it is filled in.

Proceed beyond collection only when the buyer approves the target and intended use, line/receipt joins and original commitments are traceable, timing is evidenced and unresolved records are identified. Assess whether enough mature outcomes and supplier/product diversity exist; there is no automatic 20-line or six-week ML gate. Keep prospective outcomes separate for future evaluation, and freeze chronological cutoffs before model selection. Do not use them for tuning and then claim they are an untouched test.

This pilot does not produce predictions, send purchases, contact suppliers or transfer buyer data. Purchasing decisions remain with the buyer. See `PLAN.md` and the existing dictionary for the complete field rules.
