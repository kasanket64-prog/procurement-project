# Propose delay labels from reviewed receipt coverage

This step uses original supplier promises, validated active snapshots, reconciled
receipt events, receiving reviews and cancellation signals. It proposes labels
for human acceptance; it does not train a model or rewrite the buyer's reviews.

## Approved policy and input files

Keep genuine records in the approved protected working folder outside Git. Supply
the existing `pilot_setup.csv`, `order_snapshots.csv`, `receipt_events.csv`,
`outcome_reviews.csv` and `decision_signals.csv` with their exact current headers.
Empty event/review CSVs must retain the header; a missing file blocks processing.
No workbook/CSV/dictionary schema change is required for this step.

Copy `label_policy_template.json` into that folder as `label_policy.json`. Its
approval defaults are deliberately false/blank. Complete it only after the buyer
approves the target, scope and rules, including consistency with the setup sheet's
free-text grace/returns/cancellation agreement. Match pilot_id, target_version and
approval_ref to the approved setup, assign a policy_id and record actual approved_at.
The software validates those declarations; it does not authenticate approval or
interpret arbitrary agreement prose. The report records the policy ID and hash.

The first supported policy is explicit: version 1.0, zero grace days, net accepted
quantity at the end of the original promised date, and pre-deadline cancellation
separated from post-deadline cancellation. Every reversal changes the ledger at
its recorded actual event time. A later return does not retroactively rewrite the
deadline balance. A genuine correction with a source-supported earlier event time
can change a later review's result; never backdate an event to force a label.
Other grace/returns policies require a separate implementation and approval.

## Receiving review

Record the review's actual time, known time, capture time, protected evidence
reference and the reviewer ID approved in Pilot setup. Use `pending` or `unknown`
in the review label when requesting a new calculation. An existing concrete label
that disagrees with the calculation produces `unknown` with a candidate and reason;
the software never silently replaces the original human label.

`coverage_confirmed=yes` must mean that the receiving reviewer has checked the
complete scoped line history from placement through `register_coverage_through`,
including accepted/rejected receipts and reversals, with no unresolved omissions.
It must not mean only that a few submitted rows were checked. The protected source
reference identifies that evidence. Coverage cannot extend beyond review time.
The declaration is not an independent audit or automatic proof of completeness.

For a completed status, supply complete_accepted_at and reconcile it to the ledger's
current full-quantity crossing. Partial/open states cannot claim full acceptance.
Disputes, quantity excesses, material quantity/specification changes and unresolved
completion evidence remain `unknown` for this initial policy.

Cancellation needs an existing `cancellation` Signal with actual event, known and
capture times, source, reviewer, a documented reason and buyer_verified or
independent_source verification. In Outcomes.exclusion_or_dispute, include each
active cancellation signal_id as a standalone whitespace-separated token. Missing,
unverified, unlinked or conflicting cancellation evidence remains unknown, rather
than automatically excluding an overdue failure. Review status must match the
presence of the verified cancellation event.

Weekly reviews may be appended independently; the latest actual review time is
used after resolving correction chains. Corrections use supersedes_id; broken,
cross-line, cyclic or competing links block the batch. Two independent active
reviews at the same latest review time are ambiguous and block processing.

## Decisions and time boundary

The promised date is the original supplier commitment in the destination timezone,
not the buyer's needed-by date or a later promise. Its exclusive boundary is the
start of the next local date converted to UTC. A receipt exactly at that boundary
misses the original date. Calendar/DST rules are used; unusual skipped dates need
manual review instead of an invented timestamp.

| Evidence at actual review time | Proposed label |
|---|---|
| No receiving review or conflicting/unsupported evidence | unknown |
| Original date has not closed, even if quantity was received early | pending |
| Date closed, full net acceptance at deadline, confirmed coverage through that boundary | on_time |
| Date closed, incomplete/zero net acceptance at deadline, confirmed coverage through that boundary | late |
| Date closed but coverage is absent, unconfirmed or ends too early | unknown |
| Verified linked cancellation before the boundary under the approved policy | cancelled, never binary success |
| Verified linked cancellation at/after the boundary | Preserve on_time/late only with confirmed deadline coverage; otherwise unknown |

Binary labels deliberately wait until the date closes because the approved target
is net acceptance at that boundary. Open and partial orders can be late while
remaining open/partial. A header-only receipt CSV establishes no lateness by itself;
reviewer-confirmed complete coverage is still required.

Only facts buyer-known by the selected review time enter its calculation. Later
known receipts/signals cannot rewrite an earlier review. A future-known signal
correction does not suppress its earlier version. A policy or relevant copied
evidence that postdates the review requires a fresh review. Reports retain review
and reviewer-known timestamps, supporting-evidence availability and generation
time; they are not release-time inputs. Actual label_known_at remains unset because
these are proposals, not a record of completed human label acceptance.

## Run and verify

```powershell
python ml/buyer_delay_labels.py "C:\BuyerApprovedStorage\pilot-working"
python -m unittest discover -s tests -v
```

Use the real approved external path, not this illustration. Exit code 0 returns
label proposals and counts; code 2 reports blocked input/policy errors. Files are
read-only, no network calls are made, and no records/models are written. Terminal
output contains pseudonymous order/review IDs, dates and balances; keep it private
when using genuine records and never paste it into GitHub.

Every proposal says human_label_review_required=true; model_ready and
purchase_authorized remain false. Unknown/pending/cancelled records must not become
negative training labels. Human approval of labels, source/coverage checks, a
reviewed modelling adapter and a frozen evaluation protocol remain separate gates.
Tests use only artificial temporary fixtures, never genuine buyer data.
