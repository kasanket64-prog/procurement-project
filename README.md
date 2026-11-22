# AI Supply Chain Prediction & Procurement Platform

## Engineering overview

ProcureAI explores procurement requirements, supplier discovery, quotation comparison and experimental risk analysis. It is a **prototype**, not a production procurement service or an autonomous purchasing agent.

| Component | Source | What it establishes |
| --- | --- | --- |
| Offline browser demo | [Workspace](ml/procurement_platform.html) and [Python launcher](ml/procurement_platform.py) | A local demonstration without accounts or a hosted backend |
| Supplier exploration | [Python modules](ml/) and [datasets](dataset/) | Example/researched supplier records, not independently validated live offers |
| Quotation review | [Real quotation pilot](real-pilot/README.md) | A local, human-reviewed evidence workflow, not automatic purchasing |
| Machine learning | [Training experiments](ml/) | Experimental models; no validated deployment accuracy is claimed |
| Experience design | [Frontend wireframe brief](docs/frontend-wireframes.md) | A design reference rather than proof of implemented features |

**Evaluation boundary:** simulated procurement examples, documented buyer quotations and predictive performance must be assessed separately. Human review remains necessary for eligibility, evidence quality and final purchasing decisions.

---

Public source repository for ProcureAI, a procurement workspace for supplier discovery, comparison and quotation review.

Download [the self-contained website](ml/procurement_platform.html) and open it in a browser. See the [frontend and wireframe brief](docs/frontend-wireframes.md) for the planned design and buyer journey.

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

1. Clone this public repository and review the current main branch before continuing.
2. Run the browser demo and record setup or output issues.
3. Verify whether the planned What-If simulation is complete and connected end to end; an earlier project checkpoint listed it as upcoming.
4. Reproduce model results with a chronological, leakage-safe evaluation and document recall/calibration limitations.
5. Define a small, permissioned buyer pilot; reconcile each quote and eligibility result against original documents before considering any risk prediction.

For another GitHub account, this public repository can be viewed and cloned without an invitation. Pushing changes still requires write access. This commit does not change repository visibility or access.
