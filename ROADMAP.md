# Modern supply-chain platform: phased feature roadmap

Updated 14 November 2026. This is a proposed product roadmap, not an assertion
that planned features are implemented. Expand the existing project in small,
reviewable releases. Preserve the existing terminal tools and browser demo.

## Status and verified baseline

Use these states for each deliverable: Planned, In progress, Implemented,
Tested, Awaiting review, Merged, and Buyer validated. Record the branch/commit,
test evidence and remaining gate beside a status update. Tested does not mean
merged, and artificial fixtures do not establish real-world effectiveness.

- Main baseline: `10acaaa48d3e47f7a39e37c8e140a1900bac21b9`.
- Existing procurement matching, risk experiments, terminal workflows and offline
  browser demo are prototypes; their presence does not establish production quality.
- SRS v0.3 and three architecture views are documented on this branch; owner, teacher and applicable buyer review remain pending.
- [PR #1](https://github.com/kasanket64-prog/procurement-project/pull/1): buyer instructions and blank templates; draft/unmerged at last verification.
- [PR #2](https://github.com/kasanket64-prog/procurement-project/pull/2): snapshot validation; draft/unmerged at last verification.
- [PR #3](https://github.com/kasanket64-prog/procurement-project/pull/3): receipt reconciliation; draft/unmerged at last verification.
- [PR #4](https://github.com/kasanket64-prog/procurement-project/pull/4): delay labeling and integration fixes; draft/unmerged at last verification.
- Combined tip `5d20b673d39e0f78fdfb217a0f5cecb232e6714f` passed 57 unit
  tests and 21 artificial end-to-end scenarios / 63 command runs. This evidence
  belongs to that combined tip, not to main or each earlier standalone PR head.
- No real buyer outcome validation, production model acceptance or production
  deployment is established by those checks. Historical ML scores remain subject
  to reproduction against their exact dataset and code versions.

## Phase overview

| Phase | Status now | Main result | Exit gate |
|---|---|---|---|
| 1. Requirements and progress | SRS v0.3 and architecture drafted; approval pending | Agreed scope, diagrams and tracked tasks | Reviewed SRS and measurable release criteria |
| 2. Evidence foundation | Tested at combined PR #4 tip; review pending | Validated snapshots, receipts and proposed labels | Stack reviewed; merges separately authorised |
| 3. Buyer pilot | Templates prepared; real collection pending | Consented, traceable real outcomes | Buyer confirms data permission, coverage and labels |
| 4. Modern review interface | Planned; existing demo retained | Readiness dashboard and evidence review | Artificial browser checks and buyer workflow review |
| 5. Reliable predictions | Experimental; acceptance pending | Reproducible chronological evaluation | Freeze model, calibration and thresholds before final evaluation |
| 6. Explanations and uncertainty | Planned | Reviewable prediction evidence and limits | Read-only frozen-pipeline assessment; fitted changes need fresh future evaluation |
| 7. Monitoring and feedback | Planned | Changes detected; outcomes reviewed | Repeated batches and reliable delayed-label evaluation |
| 8. Recovery planning | Planned | Feasible, explainable action comparisons | Valid constraints and human acceptance |
| 9. Integrations and documents | Planned | Reliable authorised imports | Reviewed mapping, reconciliation and failure recovery |
| 10. Secure operation and expansion | Planned | Maintainable deployment and optional planning modules | Access, backup, restore and operating checks |

## 1. Requirements, documentation and progress

- [ ] Review SRS against teacher requirements and the consenting buyer's workflow.
- [ ] Define decision time, prediction target, label policy, review capacity and acceptance metrics.
- [x] Draft SRS v0.3 and Mermaid system, evidence-flow and model-release architecture views; document lifecycle outcomes in the evidence-flow view.
- [ ] Obtain owner/teacher review of SRS and diagrams; document approval or requested changes.
- [ ] Create a GitHub phase board with linked issues and PRs; creating this file does not create that board.
- [ ] Add issue/PR templates with acceptance checks and evidence links.
- [ ] Track implementation, testing, merging and buyer validation separately.

Use [Mermaid](https://mermaid.js.org/intro/) for diagrams without adding a
runtime dependency. Do not assign unsupported percentage-complete figures.

## 2. Reliable evidence foundation

- [x] Snapshot identity, provenance, timing and correction-chain validation at the combined tested tip.
- [x] Partial receipts, accepted quantities, rejections and reversals at that tip.
- [x] Original-promise delay proposals with confirmed receipt coverage and explicit cancellation policy at that tip.
- [x] Cross-stage correction regressions and artificial end-to-end checks at that tip.
- [ ] Finish PR-stack approval and integration review before any authorised merges.
- [ ] Establish repeatable automated checks for the approved integrated branch, using artificial fixtures only.

Keep our existing Python validators. Borrow the readable validation-report idea
from [Great Expectations](https://docs.greatexpectations.io/docs/reference/learn/data_quality_use_cases/schema/)
without adding a second validation engine initially.

## 3. Consenting buyer pilot

- [ ] Confirm purpose, access, retention, cancellation interpretation and receiving-review responsibilities.
- [ ] Collect immutable decision-time snapshots and later receipt events using existing blank templates.
- [ ] Record the original supplier promise separately from later revised promises.
- [ ] Review evidence coverage before interpreting missing receipts as delays.
- [ ] Keep real records outside Git and segregated from synthetic/artificial fixtures.
- [ ] Record human label acceptance; generated proposals alone remain unsuitable for training.
- [ ] Assess coverage, class balance, history length and sample size before deciding whether model evaluation is feasible.

Begin with manual CSV exports. No external connector is needed until the buyer's
actual system and permission boundaries are known.

## 4. Modern buyer review interface

Extend the existing browser application rather than starting another dashboard.

- [ ] Responsive navigation, readable tables, keyboard access, accessible contrast and clear empty/error/loading states.
- [ ] Search, filters, sorting, pagination and saved local views where useful.
- [ ] Data-readiness cards: passed checks, blocked rows, missing evidence and last import time.
- [ ] Import preview with explicit column mappings and validation errors; do not silently coerce identifiers or dates.
- [ ] Order evidence timeline: original promise, corrections, partial receipts, rejections, reversals and reviews.
- [ ] Supplier scorecards with observation period, sample counts, unknown outcomes and evidence freshness.
- [ ] Review queue for disputed evidence, missing coverage and proposed labels.
- [ ] Comparison view for eligible quotations and independently defined What-If scenarios.
- [ ] Reviewed exports that omit private fields by default and identify their source/version.
- [ ] Optional location map when geography supports an actual buyer decision.

Prefer existing HTML/JavaScript components. Use [Plotly](https://github.com/plotly/plotly.py)
for charts when needed; select its Python or JavaScript integration to fit the
existing offline application, without assuming a new server. Use
[Leaflet](https://leafletjs.com/) only for a required map; map tiles may require
network access and attribution. Maps do not provide shipment tracking data.

## 5. Reliable prediction and experiment records

- [ ] Reproduce training commands and record dependency versions, random seed, code commit and dataset fingerprint.
- [ ] Maintain decision-time feature allowlists and fit preprocessing only on training data.
- [ ] Use chronological partitions; document repeated-order and supplier-history treatment.
- [ ] Compare a simple baseline before increasing model complexity.
- [ ] Select models and alert thresholds using validation only; keep final test out of all selection loops.
- [ ] Report precision, recall, false alerts, missed delays, class balance and relevant subgroup/sample counts.
- [ ] Preserve the existing experiment's validation constraint of at most 265 false alerts for that same validation set;
  negotiate an operational rate or workload budget separately for different batch sizes.
- [ ] Save a model with feature schema, training/evaluation ranges and a reproducible evaluation report.
- [ ] Predeclare chronological calibration/selection partitions when calibration is used; never fit or select postprocessing on the final test.
- [ ] Freeze the full model, fitted calibration/prediction-set method and threshold before one controlled final evaluation; do not recycle that test for later tuning.

Start with existing scikit-learn and file-based reports. Consider
[Optuna](https://github.com/optuna/optuna) for bounded validation searches and
[MLflow](https://mlflow.org/docs/latest/ml/tracking) for experiment tracking only
when the number of runs makes them worthwhile. Neither automatically prevents leakage.

## 6. Explainability and uncertainty

- [ ] Show model version, prediction time and evidence availability beside each score.
- [ ] Add model-compatible SHAP explanations and verify feature names/output scale.
- [ ] Separate model feature contributions from causal claims about supplier behaviour.
- [ ] Assess calibration of the phase-5 frozen pipeline using read-only diagnostics; fitting or changing a calibrator requires a fresh future evaluation.
- [ ] Investigate prediction sets/intervals using predeclared non-test calibration data before final evaluation; any later fitted change requires a fresh future test.
- [ ] Show insufficient-evidence and out-of-scope states; do not invent confidence percentages.
- [ ] Require human review before any purchasing action.

Selected: [SHAP](https://github.com/shap/shap). Conditional:
[MAPIE](https://github.com/scikit-learn-contrib/MAPIE), after assessing temporal
dependence, distribution shift and empirical coverage. Do not advertise nominal
coverage as a guarantee for changing supplier data.

## 7. Monitoring, changing suppliers and feedback

- [ ] Compare missing values, schema, new categories and input distributions between batches.
- [ ] Monitor prediction distributions and data/evidence freshness separately.
- [ ] Join human-accepted, cutoff-mature outcomes through the controlled cohort adapter for supervised evaluation and outcome monitoring; keep labels outside inference features.
- [ ] Evaluate actual precision, recall and alert workload when confirmed outcomes mature.
- [ ] Collect structured buyer feedback tied to order ID, timestamp, evidence and reviewer.
- [ ] Keep factual receipt corrections, label review and subjective supplier ratings separate.
- [ ] Support correction/dispute resolution and retain original history.
- [ ] Define alert deduplication, severity and review ownership before enabling notifications.
- [ ] Propose retraining only after reviewed evidence; no automatic deployment from feedback.

Selected: [Evidently](https://github.com/evidentlyai/docs/blob/main/quickstart_ml.mdx).
Consider [River](https://github.com/online-ml/river) only if streaming statistics
or specialised drift detection is required. Drift is an investigation signal,
not proof that a supplier is unreliable or that model accuracy has fallen.

## 8. Recovery planning and disruption simulation

- [ ] Feed approved alternatives, quantities, documented capacities, lead times, costs and effective dates through a separate recovery-constraint gate.
- [ ] Treat missing/stale constraints as unavailable/needs-review and complete but infeasible constraints as infeasible; predictions cannot supply missing facts.
- [ ] Compare waiting, expediting and split-order scenarios under explicit assumptions.
- [ ] Enforce budget, minimum quantity, capacity and documented eligibility constraints.
- [ ] Show infeasibility and missing inputs explicitly instead of fabricating an alternative.
- [ ] Present cost/service trade-offs and sensitivity to uncertain inputs.
- [ ] Model supplier-product dependencies when relationship data is available.
- [ ] Record the buyer's chosen action and subsequent outcome; never place an order automatically.

Selected: [OR-Tools](https://github.com/google/or-tools). Conditional:
[NetworkX](https://networkx.org/documentation/stable/) for dependency analysis.
Study [frePPLe](https://github.com/frePPLe/frepple) as a planning reference;
adopting its whole application is not part of this release.

## 9. System connectors and document assistance

- [ ] Choose the first connector from the consenting buyer's actual system.
- [ ] Preserve source IDs, source timestamps, receipt coverage and import provenance.
- [ ] Make repeated imports idempotent; quarantine schema changes and reconcile counts.
- [ ] Handle authentication expiry, partial failures and retries without duplicating events.
- [ ] Suggest supplier-name matches with a reviewable score; never silently merge identities.
- [ ] Extract candidate quotation/PO fields with source-page references and human verification.
- [ ] Keep approval and source-document authenticity distinct from successful extraction.

Conditional tools: [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz) for matching,
[Docling](https://github.com/docling-project/docling) for document parsing and
[Airbyte](https://github.com/airbytehq/airbyte) if supported connectors justify
the additional platform. Study [ERPNext procurement](https://github.com/frappe/erpnext/tree/develop/erpnext/buying)
for a relevant integration. Public procurement data remains separately identified
and is not assumed to contain promised/actual receiving evidence.

## 10. Secure operation, quality and optional expansion

- [ ] Before hosting private records: authentication, role/tenant boundaries, protected storage and secret handling.
- [ ] Audit access and edits; define retention, deletion and backup/restore procedures.
- [ ] Protect uploads and exports; exclude sensitive values from logs, CI artifacts and public reports.
- [ ] Browser regression checks for critical review and What-If flows.
- [ ] Automated Python checks and targeted invariant tests for histories and receipt arithmetic.
- [ ] Pin and review dependencies, licenses and copied-code attribution; document costs and offline requirements.
- [ ] Define release, rollback, service health and incident ownership before production operation.
- [ ] Add demand forecasting or inventory optimisation only as separately specified modules.

Quality candidates: [Playwright](https://github.com/microsoft/playwright),
[Hypothesis](https://github.com/HypothesisWorks/hypothesis) and
[Ruff](https://github.com/astral-sh/ruff). Growth candidates:
[DuckDB](https://github.com/duckdb), [DVC](https://doc.dvc.org/user-guide),
[StatsForecast](https://github.com/Nixtla/statsforecast) and
[Stockpyl](https://github.com/LarrySnyder/stockpyl). Demand forecasting and
inventory optimisation have separate data requirements and do not replace
delivery-delay prediction. Choose authentication/deployment technology only
after agreeing the hosting environment; do not add another app framework now.

## What to do first

1. Review the SRS and this roadmap; turn phase 1 acceptance checks into scoped tasks.
2. Finish review of the tested PR stack without changing main or merging without authorisation.
3. Run a consenting manual buyer pilot with the existing templates.
4. Build a read-only data-readiness and order-evidence screen using artificial fixtures first.
5. Evaluate real-data feasibility before model, explanation and recovery phases.

## Dependency policy

This roadmap adds no runtime packages and does not enable external services.
Core selections are Mermaid, Plotly where needed, SHAP, Evidently and OR-Tools,
introduced at their gated phases. Conditional tools require a demonstrated need,
license/version compatibility check and a small tested integration. Reuse
existing functionality first. The number of installed tools is not a completion
metric; each feature needs a working buyer flow and evidence for its claims.
