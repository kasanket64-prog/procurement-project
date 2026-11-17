# Read-only fixed-schema source preview

This partial Phase 4 preview shows the exact source → schema column names for
the existing order snapshots, receipts, outcome reviews and decision signals.
It reuses the snapshot, receipt and label validators and the offline readiness
report. It does not import, accept, correct or quarantine individual rows.

From the repository root, using a genuinely authorised working folder outside
the repository:

```powershell
python ml/buyer_import_preview.py "C:\BuyerApprovedStorage\pilot-working"
python ml/buyer_import_preview.py "C:\BuyerApprovedStorage\pilot-working" --format json
```

The default output is standalone HTML on stdout. Save it in approved private
storage using a new filename, then open it locally. Shell redirection can
overwrite existing reports; choose the destination explicitly. The command
itself writes no files, makes no network requests and follows no source links.
Exit 0 means checks completed; exit 2 means the batch is blocked. Check
`$LASTEXITCODE` in PowerShell. Neither result grants training or purchase authority.

Declared setup/permission must pass before source-header inspection. A failure
shows the existing validation reason and skips source preview. Permission is
declared, not authenticated. For each of the four supported CSVs, the preview
shows missing required columns, unexpected/duplicate column counts and exact
column-order match. Actual unexpected column names and business row values are
not displayed. No fuzzy mapping, renamed fields or automatic reordering occurs.
Only the existing blank-template schema is supported; changes need reviewed mapping.

A header match does not mean its rows passed validation. The separate pipeline
stages still reject malformed timestamps, mismatched receipt/order units,
lineage errors and invalid policy/coverage. One error blocks the batch; valid
rows are not admitted separately. An otherwise consistent but unsupported unit
is not authenticated or standardised by this preview. Unknown units still need
reviewed mappings and buyer confirmation.

The required label policy JSON and pilot setup use their existing shared
validators; this is not a mapping editor for those files. Promise events are
outside the current pipeline. Source freshness/authenticity, row-level quarantine,
evidence timelines, human acceptance and controlled exports remain pending.
The check time is not a freshness guarantee. Files are read sequentially; do not
edit during a run, and rerun after changes. Genuine errors/counts remain private.

The workspace's Evidence review section accepts the JSON report and displays
both validation stages and source-column cards with expandable required mappings.
Clear report preview removes both. Reports without the optional source-column
section continue to show their validation stages. Malformed or inconsistent source
metadata is rejected. Imported mappings remain supplied, unverified report text;
the browser does not inspect source CSVs or rerun Python validation.
Full FR27/AT15 acceptance remains pending. This command adds no runtime dependencies.
