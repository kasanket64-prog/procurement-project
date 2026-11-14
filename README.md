# AI Supply Chain Prediction & Procurement Platform

Private project for supplier discovery, procurement analysis and quotation review.

**Status (13 November 2026): prototype.** The main branch contains procurement datasets, Python analysis and matching modules, an offline HTML demo, and a separately documented real-quotation pilot. This repository snapshot does not establish production readiness or validation against real buyer outcomes.

## Start the browser demo

From the repository root with Python 3.10 or later, run: `python ml/procurement_platform.py`.

The script generates and opens `ml/procurement_platform.html` using the Python standard library. It rewrites that tracked HTML file; save local edits to it first.

Optional command-line/data tools: `python -m pip install -r requirements-terminal.txt`.
Optional machine-learning and semantic-matching dependencies: `python -m pip install -r requirements-ml.txt`.
The ML requirements include the terminal requirements. Install them only for those modules; the browser demo does not need them. The repository does not document one universal training command.

## What is in the repository

- `dataset/`: procurement records, supplier history, supplier-item data, and a public-procurement sample.
- `ml/`: procurement analysis, supplier discovery/matching, catalog search, risk and training experiments, and the browser demo.
- `real-pilot/`: input templates and a guided quotation-review pilot. Start with [real-pilot/README.md](real-pilot/README.md).

## Current limits and known issues

The real-pilot guide describes a local quotation-review engine tested with fixtures, but no real buyer records or supplier-risk outcomes have been validated. It ranks eligible quotes by documented cost only; risk remains unavailable, and a person must review source documents and make every purchasing decision.

Historical project notes reported an experimental model with 89.90% accuracy, 93.65% precision and 39.91% recall. Those figures are not reproduced or verified here. The same notes flagged low recall, possible same-day data leakage, and a prior model-saving error. Recheck the current implementation and evaluation before relying on any model result. The demo and synthetic data are not evidence of supplier performance.

## Decisions to preserve

- Keep synthetic examples clearly separate from real buyer records.
- Do not put credentials or private supplier/buyer information in GitHub.
- Do not let model scores or quote rankings make purchasing decisions.
- Keep the real-quotation pilot alongside the synthetic prototype until real-data permissions and validation are established.

## Next steps

Track progress on the [phase board](https://github.com/users/kasanket64-prog/projects/1)
and see [phase issues and status rules](docs/PHASE-TRACKING.md). Templates are
proposed on a separate branch; main is not changed by the live board.

1. Clone this private repository and review the current main branch before continuing.
2. Run the browser demo and record setup or output issues.
3. Verify whether the planned What-If simulation is complete and connected end to end; an earlier project checkpoint listed it as upcoming.
4. Reproduce model results with a chronological, leakage-safe evaluation and document recall/calibration limitations.
5. Define a small, permissioned buyer pilot; reconcile each quote and eligibility result against original documents before considering any risk prediction.

For another GitHub account, the private repository must be shared with that account or cloned through an account that already has access. This commit does not change repository visibility or access.
