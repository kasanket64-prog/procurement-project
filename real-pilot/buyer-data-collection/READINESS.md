# Buyer data readiness report

This first phase-4 screen combines the existing snapshot, receipt and label
checks into a read-only HTML report. It uses the same Python rules; it does not
replace them, import training data, confirm source authenticity or approve labels.

Use a genuinely authorised working folder **outside the repository** containing
the existing pilot setup, snapshots, receipts, outcome reviews, decision signals
and explicitly approved label policy. See SNAPSHOT-CHECK.md, RECEIPTS.md and
DELAY-LABELS.md for their preparation and limits. Do not change approval defaults
merely to pass a check. This report adds no dependencies.

From the repository root in PowerShell:

```powershell
python ml/buyer_readiness.py "C:\BuyerApprovedStorage\pilot-working" | Set-Content -Encoding utf8 "C:\BuyerApprovedStorage\readiness.html"
```

The paths are illustrative. Choose private storage and a new report filename;
`Set-Content` overwrites an existing destination. Open the saved HTML locally in
a browser. The command itself writes only to stdout and never opens a browser,
follows a source reference or sends data over the network. HTML uses no external
scripts, fonts or assets. For terminal/automation output:

```powershell
python ml/buyer_readiness.py "C:\BuyerApprovedStorage\pilot-working" --format json
```

Exit 0 means the three structural checks completed, **not** that data is approved
for training or purchasing. Exit 2 means a stage blocked: correct the stated
input/policy issue, then rerun. Later stages are explicitly skipped, never marked
passed. In PowerShell inspect `$LASTEXITCODE` for the Python exit status.

The report shows aggregate row/line/event counts and proposed label counts,
including unknown/pending/cancelled outcomes. It omits per-order rows, IDs,
quantities, source references and the input folder from successful summaries.
Validation reasons are escaped in HTML. Reports from real inputs should still
remain private and outside GitHub, including their error messages.

Every report keeps `model_ready=false`, `purchase_authorized=false` and human
review required. Review declared permission scope, source truth, receiving
coverage, disputes and each proposed label. Human acceptance and a reviewed cohort
adapter remain necessary before training. Readiness is not a supplier risk score.

Checks read files sequentially at one check time; they are not a transactional
snapshot. Do not edit inputs during a run, and rerun after any changes. There is
no upload, persistent review queue, human acceptance storage, automatic correction,
supplier scorecard or transactional source snapshot. Those remain separately scoped work.

## Preview in the procurement workspace

Generate a version 1.0 JSON report with `--format json`, save it privately, then
open the workspace's **Evidence readiness** section and select that JSON file.
The preview stays in the current page; it is not uploaded or persisted. Clear the
preview or close the page when finished. Files over 1 MB, unsupported versions,
inconsistent stages/counts or reports granting training/purchasing authority are
rejected. UTF-8 BOMs from PowerShell exports are supported.

The workspace does not rerun validators, authenticate the report, prove freshness
or read the original evidence folder. The report's check time is displayed as
supplied and is not an import time or freshness guarantee. Treat genuine report
error text and aggregate counts as private. Older unversioned JSON reports must
be regenerated. CLI and browser entry points remain available.
