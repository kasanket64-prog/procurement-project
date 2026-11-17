# Phase 2 repeatable integration checks

Related: phase issue #8; combined implementation in draft PR #4.

Run from the repository root with Python 3.10+ and the terminal requirements
(including timezone data on Windows):

```powershell
python -m unittest discover -s tests -v
python -m unittest discover -s tests -p test_buyer_pipeline_cli.py -v
```

The baseline at `5d20b673d39e0f78fdfb217a0f5cecb232e6714f` has 57 tests.
The integration test includes the original 21 scenarios plus two UTC timestamp
range regressions: 23 scenario subtests and 69 subprocess executions
of the snapshot, receipt and delay-label CLI entry points. It reuses artificial
fixture factories and the tracked blank CSV schemas. It freezes only each child
process's clock at 14 November 2026, 12:00 UTC, so approval fixtures do not expire
as the calendar advances. It does not mock the validators or reconciliation.

Scenarios cover on-time, late, open and partial delivery; missing coverage;
pre-deadline pending outcomes; rejection; reversal; pre/post-deadline cancellation;
pre-release enrichment; corrections; pending approval; broken links; invalid receipt
units; excess reversals; unapproved policy; repaired historical errors; invalid
active values; missing historical provenance; competing corrections; and UTC
underflow/overflow. Out-of-range UTC conversion must produce blocked JSON with
exit 2 rather than an uncaught traceback; representable dates retain their meaning.

Checks assert expected exit codes and JSON, no stderr, expected accepted balances
and proposed labels, `model_ready=false`, and `purchase_authorized=false` on
successful reports. Label proposals must still require human review and have no
accepted-label timestamp. Source-reference fixture text must not leak into output.
SHA-256 manifests before/after all stages must match, including the file list.
All CSVs are created outside the repository in temporary folders and cleaned up.

Some fixture fields deliberately declare `data_kind=real` and approved permission
to exercise that validation path. They are entirely artificial, not authentic
buyer permission or evidence. Never substitute genuine records in these tests.

These checks establish local software behavior only. They do not authenticate
consent, source truth, register completeness, private storage or real delivery
outcomes. No model is trained, no source document is opened, and no purchasing
decision is authorized. Passing tests does not accept the phase or authorize a
merge. The stack still needs human integration review and separate merge approval.
