# Check buyer release snapshots

This is the first implementation of the SRS snapshot-preparation controls
(FR05, FR18, FR19 and FR23). It checks declared pilot approval and release-snapshot
structure. It does not reconcile receipts, assign delay labels, export training
data or establish that a record/document is authentic.

## Prepare the files

Use an authorized working folder outside this repository. Keep the tracked blank
templates unchanged. Place copies of these two existing CSV templates there:

- `pilot_setup.csv`: complete the buyer-approved scope, roles, approval reference,
  validity, storage, target, retention and other setup decisions.
- `order_snapshots.csv`: release-time records with the exact current headers,
  including the final `supersedes_id` column.

The checker accepts CSV only. Export the corresponding workbook data to those
schemas if the workbook is the authoritative record; do not maintain contradictory
working copies. Other event-table CSVs remain part of the collection process but
are not read by this checker. Obtain genuine approval before entering business
records; do not change pending defaults merely to make a test pass.

## Run

From the repository root, with Python 3.10 or later:

```powershell
python ml/buyer_snapshot_check.py "C:\BuyerApprovedStorage\pilot-working"
```

The path is illustrative; use the location agreed with the buyer. The program
requires timezone data for the approved destination, using the same zone resolver
as the existing quotation pilot. If the computer lacks it, use the existing pilot
requirements; no new package is introduced by this checker.

Exit code 0 means `snapshot_preflight_passed`; code 2 means `blocked`, with a field
or relationship reason. Output goes only to the terminal. It contains counts and
limitations rather than buyer identifiers or source references. Input files are
never modified, and no files, network requests or purchases are created.

## Checks and limits

- Permission must be declared approved for real data, with required setup fields
  populated and the current check time within its validity window. Approval and
  permitted-use authenticity still require human verification; text alone cannot
  prove rights, storage protection or whether modelling is permitted.
- Pilot IDs and declared data kind must match throughout history; synthetic
  records are blocked even when superseded. Active snapshots must be verified_as_of;
  unverified or retrospective-unverified active versions are blocked. All-or-nothing validation means
  a failed batch must be reviewed; the tool does not silently discard rows or
  automatically move them to quarantine.
- Required identity/provenance fields must be present in every version. Active
  business fields must be present; quantities must be positive decimal strings.
  Price/currency and optional date/contract fields are checked when supplied.
  Source references are required but are not opened or independently authenticated.
- The one-site approved timezone must match. Offset-aware timestamps must satisfy
  `known_at <= decision_at = order_placed_at <= captured_at <= check time`.
  Capture must occur during the current approval window. Missing precise timing
  remains unresolved rather than being replaced with an invented timestamp.
- Snapshot IDs are unique. Originals have blank predecessor links; corrections
  reference the same line, preserve the decision instant and do not precede the
  previous capture. Each line must have one connected, noncompeting correction
  chain. Row order does not select the active version. A later supplier promise
  remains a Promise event; the checker cannot determine transcription truth.

Lineage, identity, source, permission and timing checks apply across the complete
history before resolving the active leaves. Business-value checks (quantity,
promise/date, price/currency, contract flag, verification and destination zone)
then apply to the active version only. A valid append-only correction can therefore
repair an old value such as a zero quantity without editing that original row.
Superseded business values remain audit history and never enter receipt balances
or labels. This does not allow missing provenance, foreign/synthetic records or
broken correction chains to be hidden behind a valid-looking successor.

Even a passed result always says `model_ready: false` and
`purchase_authorized: false`. Next steps are source review, required
cancellation/change events, promise/receipt/outcome reconciliation and a reviewed
modelling adapter with historical/prospective grouping. Do not send this output
directly to a trainer or interpret it as validated delivery performance.

## Verification

```powershell
python -m unittest discover -s tests -v
```

Tests use explicitly artificial in-memory/temporary fixtures, not buyer records.
They cover approved/pending/expired scope, source separation, bad fields and times,
valid and broken correction chains, strict CSV shape, read-only behavior and
the blocked command-line result. No buyer approval or real-world validity is
established by passing software tests.
