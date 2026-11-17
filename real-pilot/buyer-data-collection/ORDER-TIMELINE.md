# Private order-evidence timeline

The read-only timeline displays one exact pseudonymous order line from an
authorised external pilot folder. It reuses the existing snapshot, receipt,
review/signal and label-policy validation gates before returning any events.
An error anywhere in the supplied batch blocks the timeline; this is not
row-level quarantine or partial admission.

```powershell
python ml/buyer_order_timeline.py "C:\BuyerApprovedStorage\pilot-working" "order-line-key"
python ml/buyer_order_timeline.py "C:\BuyerApprovedStorage\pilot-working" "order-line-key" --format json
```

HTML is the default stdout output, JSON optional. Save reports with a new filename
in approved private storage; shell redirection can overwrite an earlier report.
The command writes no files, follows no source references and makes no network
requests. Exit 0 means a validated timeline is available; exit 2 means blocked.
Check `$LASTEXITCODE` in PowerShell. Neither grants label acceptance or authority
to train, purchase or contact a supplier. No runtime dependencies are added.

The report includes original snapshots and transcription corrections, receipts
(accepted, rejected and reversal), decision signals and outcome-review versions.
Each retains its source reference and event/known/capture times. Snapshot event
time is original placement, including corrections; their later capture times
remain distinct. Corrections retain predecessor IDs and superseded history.
Reversals retain the acceptance ID and quantity rather than erasing it. “Not
superseded” does not mean a receipt has not been reversed or that a declaration
is true. Review labels are declarations, not human-accepted training labels.

An active valid correction can repair historical business values while original
errors remain visible; shared provenance/lineage checks still apply to history.
Events sort by parsed event time, known time, capture time, kind and identity.
Tie-breaking is deterministic presentation, not evidence of causation. Original
time strings and offsets remain displayed. Future/unavailable records block
through the existing validators; this is not a historical cutoff-filtering tool.

Unlike aggregate readiness reports, timelines intentionally contain per-order
IDs, quantities, dates and source references. Genuine reports are private and
must remain outside GitHub; only artificial examples belong in repository tests.
References are escaped plain text, never opened or linked. No legal names,
reviewer IDs or free-text signal/dispute descriptions are added to the timeline.
Permission and authenticity remain declared, not authenticated; coverage still
needs human review. All outputs retain model_ready=false and purchase_authorized=false.

This is partial FR28/AT16 work: promise-event changes, a workspace timeline reader,
source authentication, human review decisions, controlled exports and full buyer
acceptance are not implemented. The workspace readiness reader does not accept
timeline JSON. Load the standalone HTML locally instead. Input files are read in
sequence, not as an atomic filesystem snapshot; avoid edits during the run and
rerun after changes. Blocked reports contain no events or selected order-line key.
