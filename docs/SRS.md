# AI Supply Chain Prediction and Procurement Platform

Software Requirements Specification

Version 0.3 | Draft for review | 14 November 2026

This specification defines a structured decision-support platform for discovering
suppliers, reviewing quotations, analysing delivery evidence and comparing
procurement scenarios. It is the proposed requirements baseline for the existing
project. Requirements describe the intended product; they do not certify that the
prototype already meets them. The project owner and academic guide should review
scope and priorities before implementation continues. See [the phased roadmap](../ROADMAP.md) and [architecture diagrams](ARCHITECTURE.md).

## 1 Document control and purpose

The repository is kasanket64-prog/procurement-project. This revision updates the
earlier SRS using the reviewed buyer-pilot draft PR #1 at commit 335cdf7 and the
separate DataCo validation experiment at commit 1ed1141. The earlier development
baseline was 52bbac4c6e3e992a56411237139ad65cb9187d67. Main remains at
10acaaa48d3e47f7a39e37c8e140a1900bac21b9. PR #1 is draft and unmerged. The SRS
is maintained on its own documentation branch; no experiment or pilot branch
is represented as merged or production-ready.

Version 0.3 adds the modern-feature roadmap from documentation commit a8f867a
(draft PR #5) and the combined evidence-pipeline baseline at 5d20b67 (draft
PR #4). The combined tip passed 57 unit tests and 21 artificial end-to-end
scenarios / 63 command runs. Those results do not belong to main or establish
buyer validation. This SRS update performs no new model evaluation.
The roadmap and architecture diagrams are requirements/design documents, not
installed integrations. Owner, academic and buyer approvals remain distinct.

| Revision | Change | Approval |
|---|---|---|
| 0.1 | Initial structured requirements, module boundaries and staged acceptance | Pending |
| 0.2 | Reviewed pilot correction/cancellation rules, historical/prospective collection, public-data limits and updated evidence | Pending |
| 0.3 | Modern feature requirements, architecture diagrams, ten-phase mapping and updated integration evidence | Pending |

The intended readers are the project owner, academic guide, developers, testers
and a prospective buyer reviewing the pilot. No teacher-specific SRS format has
been prescribed. This draft uses a conventional requirements structure and does
not claim compliance with a named certification or standard.

The product's longer-term direction is an Evidence Aware Supply Chain Recovery
Engine. The immediate release is narrower: reliable evidence intake, transparent
quote comparison and reproducible decision-time analysis. Recovery advice depends
on verified constraints and later acceptance gates.

Approval status is pending. The project owner approves scope; the academic guide
reviews submission requirements; a consenting buyer approves any real-data target,
data use and operational acceptance criteria. No approval or buyer is invented.

## 2 Scope and system boundary

### Included scope

The platform supports product requirement confirmation, supplier discovery,
separate synthetic demonstrations, documented quotation eligibility and cost
ranking, historical delivery analysis, independent What If scenarios, evidence
exports and evaluation reports. A permissioned buyer pilot collects versioned
order-time facts and later outcomes. Each result identifies its evidence limits.

### Excluded scope

The system does not place orders, pay suppliers, negotiate or contact suppliers
automatically. It does not promise supplier performance, infer undocumented stock
or capacity, authenticate a document merely from an operator declaration, or
automatically convert currency/units without reviewed evidence. Autonomous
recovery execution, live global supplier coverage and production-grade hosted
multi-user operation are outside the initial release.

### Release stages

Stage A establishes the specification, module contracts, regression coverage and
data collection protocol. Stage B starts a protected, manual local buyer pilot
with reconciled quotation/order evidence. Manual collection does not require an
automated importer; a reviewed mapping and validation step is required before
any collected records enter a model. Stage C evaluates real delivery prediction
on mature chronological outcomes. Stage D adds recovery
proposals only after feasibility inputs, uncertainty and user acceptance are
supported. No stage inherits acceptance from synthetic accuracy alone.

## 3 Users and operating context

| User role | Responsibility | Authority boundary |
|---|---|---|
| Buyer or procurement analyst | Confirm requirements, compare eligible quotes and review scenarios | Makes the purchasing decision outside the prediction output |
| Data steward | Obtain permitted exports, maintain IDs, provenance and access | Cannot silently relabel synthetic or unverified records as validated real evidence |
| Receiving reviewer | Reconcile partial receipts, reversals and outcome labels | Confirms evidence coverage before using absence of receipt as lateness |
| Developer or ML evaluator | Maintain modules and run controlled experiments | Uses validation for selection and preserves the designated future evaluation set |
| Pilot owner | Approve scope, access, retention, target and review capacity | Authorizes real-data use and release gates |
| Academic reviewer | Review requirements, design, tests and evidence | Academic approval does not grant buyer-data rights |

The existing browser interface is an offline generated HTML prototype. Terminal
tools provide additional matching, history and quotation workflows. A protected
local-file pilot is the initial operating assumption. Authentication, shared
storage and hosted services are future deployment requirements, not existing
prototype capabilities.

Python 3.10 or later is documented for the browser launcher. Reproduced training
used Python 3.12.14 and pinned library versions recorded in the experiment report.
Advanced semantic matching requires an additional model asset; the basic browser
launcher does not require it. A supported browser/hardware matrix must be agreed
before buyer release; no GPU or minimum hardware claim is established here.

## 4 Structured product architecture

### Logical modules

| Module | Owns | Existing starting point |
|---|---|---|
| Requirement and discovery | Product confirmation, catalog retrieval and lead provenance | procurement_search.py, supplier_matcher.py, catalog_search.py |
| Evidence and intake | Versioned identities, permissions, snapshots and timestamp validation | real_intake.py and quotation_schema.py; buyer_snapshot_check.py on draft PR #2/#4; general buyer adapter planned |
| Quotation review | Commercial eligibility, exclusions and exact cost ranking | real_procurement.py and quotation_mapping.py |
| History and prediction | As-of features, evidence counts, model inference and uncertainty labels | procurement_history.py, procurement_risk.py |
| Scenario comparison | Independent baseline/scenario inputs and comparable outputs | procurement_ai.py and quotation_demo.py |
| Evaluation and artifacts | Mature chronological splits, experiment policies and model manifests | procurement_training.py, corrected trainer and validation scripts |
| Presentation and reporting | Browser/CLI interactions, explanations and controlled exports | procurement_platform.py, HTML template and report outputs |
| Recovery proposals | Verified feasibility checks and evidence-linked alternatives | Planned; no validated recovery engine exists |
| Receipts and label review | Accepted quantities, reversals, coverage and human label acceptance | buyer_receipts.py and buyer_delay_labels.py on draft PR #3/#4; human acceptance workflow planned |
| Monitoring and feedback | Batch quality, delayed-label evaluation, dispute/feedback history | Planned; no automatic retraining or deployment |

The intended dependency flow is input adapters to validation and evidence, then
shared domain functions, then presentation/export. Training is an explicit
evaluation activity and must not run when a user requests a recommendation.
Quotation review must not load the synthetic model to manufacture real risk.
Browser and CLI adapters should use the same documented business rules.

### Architecture views and implementation boundary

The companion [architecture document](ARCHITECTURE.md) contains three editable
Mermaid diagrams and local SVG previews: logical system components,
evidence-to-label processing, and controlled model evaluation/release. Each
diagram also has a plain-language explanation. The PDF includes the same views.
These show intended boundaries, not a deployed service topology.

Current foundations remain local Python domain functions with browser/CLI
adapters. Planned adapters, monitoring and recovery modules are added only at
their acceptance gates. External access always passes permission, mapping and
validation checks. Raw buyer data and identity mappings remain outside Git.
The model registry is a logical controlled manifest/artifact store; it does not
require MLflow or a hosted service. Training never runs on a recommendation request.

### Repository structure and migration

Use docs for the SRS and design decisions, ml for existing entry points and shared
logic, tests for regression coverage, real-pilot for blank pilot schemas and
guidance, and ignored models for generated model artifacts. Keep genuine buyer
records outside Git. Label existing datasets as synthetic or public evidence as
appropriate; the current dataset directory is not proof of real supplier outcomes.

Module boundaries are the first structural requirement. A later physical package
reorganization requires its own plan, caller inventory and regression checks.
Keep working entry points compatible during any migration. Do not introduce a
web framework, database or service layer until a reviewed operational requirement
needs one. This SRS authorizes no code migration by itself.

### Core contracts

Discovery returns product identity, match basis and source kind. Quote review
returns eligibility, exclusion reasons, documented total, cost rank and purchase
authorization false. Prediction returns target/model version, decision timestamp,
evidence counts, score and availability limits. Scenario comparison returns the
unchanged baseline, changed inputs and matched differences. Recovery proposals
must additionally identify constraints, source evidence and unresolved assumptions.

## 5 Functional requirements for discovery and quotations

Each FR identifier is stable. Must requirements are release gates for their stated
stage; Should requirements may be deferred with a recorded reason. Existing
foundations require acceptance testing and are not automatically complete.
For the manual collection part of Stage B, a named reviewer applies the documented
rules. The blank workbook records inputs and offers dropdowns; it does not enforce
relationship, permission or outcome correctness. Automated controls require a
separately tested implementation before the corresponding feature is released.

### FR01 Requirement capture

The system shall capture product/specification, quantity/unit, destination,
required delivery and budget/currency, making unknown values explicit. Priority:
Must, Stage B. Acceptance: missing or ambiguous essentials trigger confirmation
or an unavailable result rather than a guessed requirement.

### FR02 Product and supplier discovery

The system shall retrieve relevant products and supplier leads with the match
basis and provenance. It shall distinguish historical leads from current offers.
Priority: Must, Stage B. Acceptance: a public award record is never presented as
verified stock, a current quote or evidence of current delivery capacity.

### FR03 Product and commercial confirmation

The system shall require confirmation of exact product, unit, quantity and any
brand/substitution constraints before a genuine quote comparison. Priority: Must,
Stage B. Acceptance: unsupported currency/unit/pack conversion and unresolved
alternatives are excluded with reasons.

### FR04 Evidence separation

The system shall keep real, synthetic, public and unverified evidence identifiable
and prevent synthetic fixtures from entering real performance evaluation.
Priority: Must, all stages. Acceptance: a synthetic source submitted to real quote
review is rejected; an unverified record cannot silently become real evidence.

### FR05 Versioned intake

The system shall preserve source references, stable IDs, consent scope, event time,
buyer availability and capture time, with append-only corrections. Priority: Must,
Stage B. Acceptance: a later promise/quantity change retains its predecessor and
cannot overwrite an original decision snapshot.

### FR06 Quote eligibility

The system shall verify source permission, identity, exact specifications,
quantity, unit, currency, destination, expiry, availability, complete costs and
delivery compatibility before ranking. Priority: Must, Stage B. Acceptance:
expired, future-known or commercially mismatched quotes receive no cost rank.

### FR07 Exact cost ranking

The system shall rank eligible quotes by documented total using decimal arithmetic
and give equal totals tied ranks. Priority: Must, Stage B. Acceptance: decimal
ties remain ties, ineligible quotes remain unranked and no quality/risk score is
implied by a low price.

### FR08 Human quotation review

The system shall show exclusions, terms needing review, source references and
risk unavailable where unsupported. Priority: Must, Stage B. Acceptance: no report
authorizes a purchase; a buyer can reconcile each amount and exclusion to sources.

## 6 Functional requirements for prediction and scenarios

### FR09 As-of historical features

The system shall use only facts available at the decision time for historical
features, retaining open orders in workload histories. Priority: Must, Stage C.
Acceptance: changing a future or undisclosed outcome cannot change earlier
features, and same-day data follows the recorded timestamp precision rule.

### FR10 Qualified risk estimates

The system shall identify target, model/baseline version, decision date, history
counts, unknowns and whether a score is experimental. Priority: Must, Stage C.
Acceptance: synthetic model scores are not described as validated real-world
probabilities; new suppliers or missing history are explicitly identified.

### FR11 Independent What If scenarios

The system shall derive each scenario from an immutable original request and a
fixed evidence timestamp. Priority: Must, Stage B for cost/history comparisons.
Acceptance: scenarios do not accumulate changes or mutate the original; no-match,
newly eligible and removed suppliers are compared by stable identity.

### FR12 Feasible scenario semantics

The system shall preserve total budgets when quantity changes and require revised
documented offers where quantity affects a quote. Historical outcomes shall not
change because a user changes a deadline. Priority: Must, Stage B. Acceptance:
unknown capacity/lead time is not treated as a verified constraint or a causal
effect of the scenario.

### FR13 Versioned targets and labels

The system shall store target definitions, original commitments, partial receipts,
reversals, cancellations and label availability separately from predictors.
Priority: Must, Stage C. Acceptance: open/unknown/cancelled lines are not silently
labelled on time; post-decision revisions do not rewrite the original target.

### FR14 Chronological evaluation

The system shall separate training, validation and designated future evaluation
by calendar boundaries and label maturity. Priority: Must, Stage C. Acceptance:
preprocessing fits training only, selection uses validation only, no decision day
is split, and labels unavailable at a training cutoff are excluded from fitting.

### FR15 Controlled artifacts and thresholds

The system shall record model hash, feature schema, dependency versions, training
cutoffs, target and any selected threshold policy. Priority: Must, Stage C.
Acceptance: reloaded artifacts reproduce reference scores/decisions under the
recorded environment and the threshold cannot be silently applied to another model.

### FR16 Honest evaluation reporting

The system shall report precision, recall, false alerts, missed delays, prevalence,
baselines and selection protocol, with uncertainty/calibration limits. Priority:
Must, Stage C. Acceptance: validation-selected results are not labelled final-test
or real-world improvement; a failed comparison may explicitly retain the baseline.

## 7 Functional requirements for control and recovery

### FR17 Traceable exports

The system shall export reviewed results with source/input/engine identifiers,
decision time, exclusions and evidence limitations, preserving earlier reports.
Priority: Must, Stage B. Acceptance: existing report files are not silently
overwritten and export does not send data to third parties automatically.

### FR18 Access and retention controls

The deployment shall enforce approved access, protected storage, retention and
withdrawal procedures for buyer records and identity mappings. Priority: Must,
Stage B. Acceptance: filled records remain outside Git; absent/expired permission
blocks real-data use. An ignore rule alone is not accepted as access control.

### FR19 Actionable validation errors

The system shall reject malformed records and report the field or unresolved
relationship without inventing defaults. Priority: Must, Stage B. Acceptance:
duplicate IDs/keys, impossible timestamps and mismatched units do not yield a
healthy rank or silently turn missing values into zero.

### FR20 Evidence constrained recovery proposals

The system shall propose recovery alternatives only when required price, quantity,
capacity, commitment and destination evidence supports feasibility. Priority:
Should, Stage D. Acceptance: missing constraints produce unavailable/needs-review
results, not fabricated alternative suppliers or guaranteed delivery.

### FR21 Explainable recovery comparison

The system shall explain each proposed alternative's constraints, evidence age,
estimated cost/time effects and unresolved uncertainty. Priority: Should, Stage D.
Acceptance: model sensitivity is distinguished from causal delivery improvement;
the buyer can trace each stated constraint to a source.

### FR22 Human purchasing authority

The system shall leave selection and purchasing authorization with the buyer.
Priority: Must, all stages. Acceptance: no workflow sends an order, payment,
supplier message or commitment without a separately authorized human action.

### FR23 Original-snapshot correction integrity

The collection process shall append transcription corrections with a new
snapshot_id and a supersedes_id referencing the previous snapshot for the same
pilot and order line. Originals have no supersedes_id. Priority: Must, Stage B.
Acceptance: one reviewed active chain is resolved per line; missing links, cycles,
multiple roots and competing corrections remain quarantined. Later supplier
revisions remain Promise events, not corrections to the original commitment.

### FR24 Required cancellation and scope-change evidence

The collection process shall retain cancellation and material quantity or
specification changes as sourced Signal events with event_at, known_at,
captured_at, reviewer_id and source_ref, linked from the outcome review.
Priority: Must, Stage B. Acceptance: missing timing remains unresolved; a buyer
approves before/after-deadline treatment and any grace before labels are assigned.
An after-deadline cancellation cannot silently erase an already evidenced missed
deadline. Exclusions and deviations are reported separately from successful orders.

### FR25 Controlled buyer-data preparation

The system shall validate an explicitly reviewed mapping from the buyer's source
exports and collection schemas before producing model-ready order lines.
Priority: Must, before Stage C. Acceptance: IDs, units, active snapshot versions,
promise evidence, receipt reconciliation, availability and collection group are
checked; unresolved records are quarantined with reasons. Neither the blank
workbook nor the public-data research preparation is accepted as this adapter.

### Modern platform requirements

These requirements extend the existing rules; they do not replace them. Stage
letters A-D describe release gates; phase numbers refer to ROADMAP.md. A Must
requirement applies before its named capability is released, not as a claim that
every later capability is required for the initial manual pilot.

### FR26 Responsive review workspace

The interface shall provide labelled controls, search, filters, sorting and pagination for review tables, with explicit loading, empty, partial and failed states. Saved views shall store preferences without exposing buyer records.
Priority: Must, Stage B, phase 4. Acceptance: Keyboard-only review reaches every action; filtering preserves source IDs and visible totals; blocked records never appear as healthy results; narrow layouts retain readable content.

### FR27 Data-readiness dashboard and import preview

The system shall preview source-to-schema mappings and show passed checks, quarantined rows, permission state and import/evidence freshness before accepting a batch. Schema changes shall require reviewed mapping.
Priority: Must, Stage B, phase 4. Acceptance: Missing columns, invalid timestamps and unknown units produce specific errors; preview is read-only; invalid rows cannot bypass the existing shared validators.

### FR28 Order evidence timeline

The system shall present original snapshots, correction links, promise changes, receipts, rejections, reversals and outcome reviews with source and event/known/capture times.
Priority: Must, Stage B, phase 4. Acceptance: A partial receipt followed by a reversal displays both events; valid active corrections repair old business values while historical provenance and lineage remain checked; originals are preserved.

### FR29 Supplier scorecards with denominators

The system shall show confirmed outcome counts, unknown/pending/cancelled counts, observation window, product/site scope and freshness beside performance summaries.
Priority: Must, Stage B, phase 4. Acceptance: Unknown outcomes are not counted as on-time deliveries; a zero eligible denominator displays unavailable; changing filters recomputes both numerator and denominator.

### FR30 Review queue and controlled exports

The system shall queue missing coverage, disputes and proposed labels with reviewer decisions and reasons. Exports shall identify filters, source/engine versions and limitations and omit private fields unless explicitly authorised.
Priority: Must, Stage B, phase 4. Acceptance: An unaccepted label proposal remains model_ready=false; export preview contains no excluded identity fields; earlier reports and source records remain unchanged.

### FR31 Interactive analytical views

The interface shall offer delivery distributions, time trends and independent scenario comparisons with units, legends, denominator counts and a tabular alternative. Location maps are optional when decision-relevant.
Priority: Should, Stage B, phase 4. Acceptance: Chart filters match table totals; risk meaning is not conveyed by colour alone; offline operation or missing map tiles gives a readable fallback, not a false tracking status.

### FR32 Prediction explanation contract

Each explanation shall identify model/feature schema, prediction time, score scale, explainer/background version, feature contributions and unavailable inputs. SHAP is the selected candidate, subject to model compatibility.
Priority: Must, Stage C, phase 6. Acceptance: Explanation features match inference inputs; contributions reconcile to the supported model output within recorded numerical tolerance; tests reject schema mismatch; no causal delivery claim is inferred.

### FR33 Calibration and insufficient-evidence states

The system shall distinguish risk scores from calibrated probabilities and report calibration evidence and unavailable/out-of-scope cases. Prediction intervals or sets require a separate suitable calibration protocol.
Priority: Must, Stage C, phase 6. Acceptance: No synthetic score becomes a verified buyer probability; missing prerequisites show unavailable; MAPIE coverage is measured on the agreed temporal evaluation and never asserted unconditionally under shift.

### FR34 Experiment manifest and constrained selection

Each comparison shall record dataset fingerprint, cohort/label policy, code/environment, features, split boundaries, seed and threshold search. Training transforms fit only training rows.
Priority: Must, Stage C, phase 5. Acceptance: Only validation selects settings; final test remains outside all selection loops. The existing DataCo comparison retains its <=265 false-alert constraint on that same validation set; a new buyer budget requires separate agreement.

### FR35 Batch monitoring and delayed-outcome evaluation

Monitoring shall compare schema, missingness, unseen categories, input/score distributions and freshness against a versioned reference. Confirmed mature outcomes shall separately support precision, recall and workload reports.
Priority: Must, Stage C, phase 7. Acceptance: A changed batch produces a reproducible report; missing labels prevent claims of measured accuracy change; no drift flag alone declares a supplier unreliable. Evidently is the selected candidate.

### FR36 Structured feedback and disputes

Feedback shall link to scoped order/prediction IDs, reviewer, known/capture times, evidence, feedback type and correction history. Subjective ratings, factual corrections and human label acceptance shall remain distinct.
Priority: Must, Stage B, phase 7. Acceptance: A negative opinion cannot overwrite accepted quantities or a factual label; disputes remain visible and excluded where policy requires; future feedback cannot change earlier decision-time features.

### FR37 Controlled alerts and model promotion

Alert rules shall define severity, deduplication, reviewer ownership and workload limits. Retraining candidates and model promotion shall require recorded evaluation and authorised review.
Priority: Must, Stage C, phase 7. Acceptance: Repeated processing does not duplicate an alert; feedback/drift alone cannot retrain and deploy; every promoted model has a reviewed manifest and a rollback reference.

### FR38 Constrained recovery optimisation

The system shall compare waiting, expediting and split-order choices only against approved supplier/product eligibility, sourced costs, quantities, capacities, destinations and time constraints.
Priority: Should, Stage D, phase 8. Acceptance: Known capacity/budget limits hold; infeasible and incomplete-input cases are explicit; outputs show objective, assumptions, solver status and limits. OR-Tools is the selected candidate; no output executes a purchase.

### FR39 Dependency exposure and sensitivity

The system shall optionally model sourced supplier-product-site relationships and compare outcomes under explicit disruption assumptions. NetworkX is conditional on needing graph analysis.
Priority: Should, Stage D, phase 8. Acceptance: An unknown dependency remains unknown; scenario inputs and baseline are immutable; simulated effects are labelled conditional rather than observed or guaranteed.

### FR40 Authorised idempotent connectors

A connector shall enforce permission scope, stable source IDs, source availability/retrieval times, reviewed mapping, schema version and reconciled import counts, with retry and partial-failure handling.
Priority: Must, Stage B, phase 9. Acceptance: Reimport/retry creates no duplicate events; revoked permission blocks access; schema drift is quarantined; incomplete export coverage cannot establish absence of a receipt. Start with one buyer-specific adapter.

### FR41 Assisted document extraction and entity matching

Extracted fields and suggested name matches shall retain source page/location, extraction/matching version and review status. Docling and RapidFuzz are conditional candidates.
Priority: Should, Stage B, phase 9. Acceptance: An ambiguous quantity/date or supplier match stays unresolved until human verification; extraction cannot establish authenticity or silently merge identities; original evidence remains available.

### FR42 Hosted access and tenant isolation

Before shared hosting of private records, access shall use authenticated identities, role/tenant checks, protected transport/storage and managed secrets. The deployment design shall define upload/export protections and audit access.
Priority: Must, Stage B, phase 10 before hosting. Acceptance: Cross-tenant and unauthorised access tests fail closed; no credentials or buyer data enter Git, public logs or CI artifacts. Local pilot protection remains required before this later hosting phase.

### FR43 Operational recovery and retention

The operator shall document service health, backup/restore, interrupted import recovery, retention/deletion, incident ownership and release rollback. Audit and backup retention shall follow approved obligations.
Priority: Must, Stage B, phase 10 before hosting. Acceptance: A recorded restore and rollback exercise succeeds in a controlled environment; partial writes are detectable/recoverable; deletion follows the approved scope rather than silently destroying audit evidence.

### FR44 Dependency and regression governance

Every adopted component shall have a documented need, pinned compatible version, reviewed licence/attribution, data transmission/offline requirements and focused checks. Existing browser and CLI contracts shall be preserved.
Priority: Must, Stage A onward, phases 1 and 10. Acceptance: The documentation-only SRS update installs no runtime packages; each later change records affected callers/contracts and tests; artificial fixtures alone enter public/CI test artifacts.

### FR45 Separately gated planning extensions

Demand forecasting, inventory optimisation and streaming learning shall require separate targets, data, baselines and acceptance protocols. StatsForecast, Stockpyl and River are conditional references, not current dependencies.
Priority: Should, Stage D, phase 10 optional. Acceptance: An extension has its own approved specification and chronological evaluation; demand predictions are never reported as validated delivery-delay predictions; scope expansion cannot bypass earlier gates.

## 8 Data requirements and interfaces

### Data entities

| Entity | Core identity and fields | Important relationship |
|---|---|---|
| Pilot permission | Pilot ID, approved purpose/fields, roles, expiry, retention, approval reference | Governs real records and identity mapping |
| Supplier and product | Stable scoped IDs, product specifications/unit and mapping provenance | Similar names alone do not establish identity |
| Order snapshot | Snapshot/line ID, optional supersedes_id, decision/placement, original supplier promise, quantity/unit, destination and timezone | Immutable view at release; one resolved correction chain per line; later facts are events |
| Promise or signal event | Event ID, line ID, fact/version, event time, known time, source, predecessor | A later-known fact cannot enter an earlier decision |
| Receipt event | Line/site, accepted/rejected/reversed quantity, unit, event/known times | Reconciles accepted quantity and partial deliveries |
| Outcome review | Target version, status/label, completion, register coverage, reviewer and availability | Outcome evidence is separated from predictors |
| Quotation | Quote/version, supplier/product/line terms, exact quantity/total/currency, issue/receipt/expiry and source | Eligibility precedes cost ranking |
| Model and policy | Artifact/hash, feature/target version, cutoffs, dependencies and threshold | Threshold belongs to one identified artifact |
| Scenario or proposal | Baseline ID, input changes, fixed evidence timestamp, compared records and limits | Retains original and does not execute a purchase |

### Modern feature data contracts

Import manifests record source/schema/mapping versions, batch fingerprint, row
counts, retrieval/as-of time, permission and quarantine results. Explanation
records bind prediction/model/schema and background configuration; monitoring
records bind reference/current batches, metrics, thresholds and label maturity.
Feedback records preserve reviewer authority, type, evidence and correction links.
Recovery records retain baseline, objective, sourced constraints, solver status
and human decision. These are proposed logical contracts, not new workbook/CSV
columns. Schema implementation requires a versioned mapping and separate review.
Raw buyer records, credentials and identity maps must never enter this repository.

### Availability and precision rules

Store event time, buyer-known time and project capture time separately. Use only
facts known by the decision instant. If only dates are evidenced, exclude same-day
history conservatively rather than inventing midnight/order. Retain offset-aware
timestamps and IANA destination zones. Monetary comparisons use decimal strings;
units, currencies and pack identities require exact documented compatibility.

For the proposed real buyer target, decision_at equals order placement/release.
The original promise must be a supplier commitment already known then. A buyer
needed-by date is a distinct field. A later first acknowledgement must not be
backfilled; use an explicitly approved later decision definition or exclude the
line from that initial experiment.

The historical synthetic target is actual completion after promised date. The
buyer pilot proposes full original quantity accepted by original commitment,
including carefully reviewed open-overdue cases. These are different target
versions; their results must not be merged or compared as identical labels.

### Buyer collection scope and outcome rules

Proposed pilot scope is one consenting buyer, one receiving site and one product
family. Use 20-30 historical lines from a defined consecutive window/export rule
to check ingestion, followed by all new releases in the agreed scope for four
weeks. Review weekly and around week six, continuing open-line follow-up until
outcomes mature. This is a process dry run, not a minimum training sample or a
promise of model readiness. Buyer approval determines the actual dates/workload.

Older and new records from the same buyer may share stable identities, but the
historical and prospective collection groups remain traceable through protected
source references and source exports. A later receipt for an old open line does
not create a new prospective order. A historical reconstruction without verified
release-time availability stays retrospective_unverified and ineligible for the
release-time prediction cohort. Prospective records are not automatically valid.

The draft pilot has 87 dictionary entries across five business tables: Order
snapshots (26), Promise events (14), Receipts (14), Signals (16), Outcomes (17).
Pilot setup separately records approval, target, access and retention decisions.
Workbook, CSV and dictionary must agree on names, ordering and conditional
requirements. Supersedes links are required for corrections, not original rows.
Cancellation/material-change events are required when they occur; other enrichment
signals remain optional. Template versions and source mappings must be recorded
before import. The current schema is a reviewed proposal, not a populated dataset.

At combined draft tip 5d20b67, snapshot, receipt and label commands implement
read-only preflight/proposals, not a general model-ready importer. Label policy
must be explicitly approved; the implemented first policy uses zero grace and
net acceptance at original local date-end. Binary proposals wait for that date
to close, including early-completed orders. Register coverage must reach the
exclusive next-local-day boundary. Nonzero grace and material scope changes
remain unsupported/unknown rather than silently falling back to this policy.
Every generated proposal still requires human review and is not model-ready.

The date-based delivery target uses the original supplier-committed deadline in
the destination timezone, with only an expressly approved grace period. Full
delivery means cumulative original quantity accepted at the original destination,
after reviewed partial receipts, rejections and reversals. Dispatch, invoicing or
a carrier estimate alone cannot establish buyer acceptance. No exact receipt
time is invented for a date-only source; unresolved precision stays quarantined.

On-time requires reconciled full acceptance by the deadline. Late requires full
acceptance afterwards or a missed deadline supported by confirmed receipt-register
coverage through that deadline. Otherwise keep pending/unknown distinct. Proposed
cancellation treatment retains pre-deadline cancellations as cancelled/excluded;
for post-deadline cancellations preserve an evidenced late label with cancelled
delivery status. The buyer must approve that policy or document deviations and
counts before labelling. Scope changes retain original commitments and reasons.

### Public and connected-source boundary

DataCo version 5 is a separately stored historical research source with
publisher-claimed company data. Its shipping-delay proxy, final-status filtering,
unverified field availability and absent receipt/disclosure evidence do not
validate current buyer delivery risk. It must not be appended to the buyer cohort
or joined to synthetic suppliers by name. Public tender awards are discovery
evidence, not verified stock, current offers or observed delivery outcomes.

Future marketplace/ERP connections require authorized access, documented reuse
scope, stable source IDs and retrieval/as-of times. Offers must show freshness
and missing values; advertised delivery and public reviews remain claims unless
matched to permitted transaction/receipt evidence. No live app integration,
automatic refresh schedule or global supplier coverage exists in the initial
pilot. Any connector is a later scoped requirement, not implied by this SRS.

### Interfaces and storage

Browser/CLI interfaces confirm essential inputs, display reasons and identify
source kind. File interfaces include the existing quotation JSON schema and the
new blank collection workbook/CSVs; these formats are not directly interchangeable.
A reviewed import adapter and validation report are required before model use.

Preserve existing CLI entry points and JSON contracts unless a versioned migration
is approved. No REST API, hosted database or multi-user backend is required by
Stage A. If later deployed, define API authentication, authorization, schema
versioning, concurrency and backup behavior before acceptance.

## 9 Nonfunctional requirements

| ID | Requirement and verification | Stage |
|---|---|---|
| NFR01 | Integrity. Invalid input shall fail visibly; corrections preserve predecessors; report overwrite tests pass. | B |
| NFR02 | Privacy. Verify approved users/storage, separate identity key, no real records in Git and no unapproved transmission. | B |
| NFR03 | Reproducibility. Record environment/data/model hashes and seeds; reference reload scores match within 1e-12 and threshold decisions match. | C |
| NFR04 | Maintainability. UI/CLI shall call shared business rules; new nontrivial logic has focused regression coverage and documented contracts. | A onward |
| NFR05 | Usability. Inputs have labels/units; keyboard access, focus and errors are visible; exclusions and unavailable evidence are readable. Verify in the agreed browser matrix. | B |
| NFR06 | Performance. Proposed target: local ranking/comparison P95 <=5 seconds for 500 eligible supplier records; as-of feature build <=60 seconds for 50,000 orders. Benchmark on recorded hardware; owner approval pending. | B and C |
| NFR07 | Operational recovery. Demonstrate buyer-approved backup/restore and interrupted-write handling before protected real-data use. | B |
| NFR08 | Model safety. Load only trusted, registered artifacts whose hash/schema match the policy; do not deserialize arbitrary uploaded pickle files. | C |
| NFR09 | Compatibility. Publish tested Python/library/browser versions; basic browser launch remains independent of semantic model downloads. | B |
| NFR10 | Accessibility of evidence. Every displayed recommendation has a source kind, decision time and understandable limitation; no colour-only decision meaning. | B onward |
| NFR11 | UI resilience. Verify keyboard navigation, narrow layouts, empty/loading/error states and table/chart equivalence in the agreed browser matrix. | B |
| NFR12 | Isolation. Before hosting, exercise role and tenant denial tests, upload/export boundaries and secret/log inspection. | Before hosted private use |
| NFR13 | Monitoring integrity. Version references, metric rules and label-maturity cutoffs; rerunning a batch reproduces its report without duplicate alerts. | C |
| NFR14 | Component governance. Record licence, attribution, supported versions, external transmissions and offline limitations before adopting each component. | A onward |
| NFR15 | Release recovery. Demonstrate documented backup restore, partial-import recovery and model/application rollback before the relevant operational release. | Before operational release |

Performance figures are proposed acceptance targets, not reproduced benchmark
claims. Precision/recall acceptance levels and review budgets remain buyer-specific
open decisions; the synthetic 32-false-alert comparison is not a production SLA.

## 10 Main use cases and acceptance tests

### User flows

UC01 Discover: the buyer describes a requirement, confirms a product/specification,
reviews separated leads/demo matches and prepares an RFQ draft. No exact match
leads to clarification, not an invented specification or offer.

UC02 Review quotations: a reviewer loads permitted documented offers, validates
identity/terms/timestamps, inspects eligibility reasons and compares cost ranks.
The buyer checks original documents and makes the decision separately.

UC03 Compare scenarios: a user saves the original request, changes one input and
reviews matched differences at the same evidence timestamp. Insufficient evidence
remains unavailable, and independent scenarios do not alter the original.

UC04 Evaluate prediction: the evaluator freezes target and chronological cutoffs,
fits only mature training data, selects on validation, freezes artifact/policy and
opens future evaluation only under the agreed protocol. No improvement is a valid
outcome; the original model may remain selected.

UC05 Collect buyer evidence: the steward records approval, captures release
snapshots, appends revisions/receipts and reconciles labels with a receiving
reviewer. Missing permission or availability evidence stops real-data use.

UC06 Review recovery proposals: after Stage D gates, the buyer examines feasible
alternatives and their evidence/uncertainty. Unverified capacity blocks a
feasibility claim; a proposal alone cannot authorize a purchase.

### Acceptance and requirement traceability

| Test | Scenario and expected result | Requirements |
|---|---|---|
| AT01 | Ambiguous product/unit/currency requires confirmation; historical lead never becomes a current offer. | FR01–FR03 |
| AT02 | Synthetic or unauthorized real input is blocked in real review; unknown evidence stays labelled. | FR04–FR05, FR18 |
| AT03 | Expired/future-known/mismatched quote is unranked; exact decimal ties remain tied. | FR06–FR08 |
| AT04 | Changing future outcomes leaves earlier features unchanged; open prior orders remain in workload. | FR09, FR13 |
| AT05 | Each scenario starts from original; quantity changes preserve total budget and do not invent revised prices. | FR11–FR12 |
| AT06 | Calendar splits keep days intact and exclude immature fitting labels; test rows cannot enter validation selection. | FR14, FR16 |
| AT07 | Model hash/schema/threshold mismatch fails; trusted saved model reproduces reference decisions. | FR10, FR15 |
| AT08 | Existing export is not overwritten; malformed IDs/times yield specific errors and no healthy rank. | FR17, FR19 |
| AT09 | Missing capacity/commitment evidence blocks recovery feasibility and flags uncertainty. | FR20–FR21 |
| AT10 | No output authorizes/sends a purchase, payment or supplier message automatically. | FR22, FR08 |
| AT11 | Original snapshot has no predecessor; valid transcription correction links the same line; broken, cyclic or competing chains stay quarantined. | FR05, FR23, FR25 |
| AT12 | Cancellation/change requires a sourced event and known time; after-deadline cancellation preserves evidenced lateness under the approved rule. | FR13, FR24 |
| AT13 | Historical/prospective groups remain traceable; unverified timing, mismatched schemas/units and public/synthetic rows cannot enter the buyer modelling cohort. | FR04, FR09, FR25 |
| AT14 | Keyboard and narrow-screen review works; filter totals and empty/error states remain accurate. | FR26 |
| AT15 | Import preview catches schema/time/unit errors without changing source files or admitting invalid rows. | FR27 |
| AT16 | Evidence timeline retains original errors/corrections and accepted/rejected/reversed receipt history. | FR28 |
| AT17 | Supplier counts reconcile to the selected cohort; unknowns are separate and zero denominators unavailable. | FR29 |
| AT18 | Unaccepted proposals stay out of training; reviewed exports exclude private fields and preserve prior reports. | FR30 |
| AT19 | Chart/table totals match; missing map/network support gives a fallback without invented live tracking. | FR31 |
| AT20 | Model-compatible explanation contributions reconcile on the declared output scale; schema mismatch blocks. | FR32 |
| AT21 | Calibration protocol is separate from final evaluation; unavailable/shifted cases do not receive fabricated confidence. | FR33 |
| AT22 | Run manifest binds data/code/splits; validation alone selects settings and preserves the applicable alert budget. | FR34 |
| AT23 | Changed batch yields a repeatable drift report; absent labels cannot yield measured accuracy-change claims. | FR35 |
| AT24 | Subjective ratings cannot rewrite receipts/labels; factual corrections preserve provenance and as-of behaviour. | FR36 |
| AT25 | Repeated batch alerts deduplicate; drift/feedback cannot auto-promote a model; rollback reference is retained. | FR37 |
| AT26 | Recovery respects capacity/budget; infeasible/missing-input/time-limited cases remain explicit and execute nothing. | FR38 |
| AT27 | Dependency scenarios preserve their baseline and expose unknown links and assumptions. | FR39 |
| AT28 | Connector retries do not duplicate events; revoked permission/schema drift/partial coverage fail safely. | FR40 |
| AT29 | Ambiguous extracted fields and name matches require source-linked review; no silent identity merge occurs. | FR41 |
| AT30 | Unauthorised/cross-tenant access is denied; uploads/exports and logs expose no prohibited private content. | FR42 |
| AT31 | Controlled restore, interrupted-import recovery, rollback and retention/deletion checks follow the approved procedure. | FR43 |
| AT32 | New component has a reviewed compatibility/licence record and targeted checks; existing entry points remain compatible. | FR44 |
| AT33 | Optional forecasting/inventory/streaming extension has separate approved data, target and evaluation. | FR45 |

UC07 Review modern workspace: preview a batch, resolve readiness issues, inspect
an order timeline, filter supplier evidence and review proposed labels without
rewriting sources. UC08 Monitor and dispute: inspect changed-batch reports,
submit sourced feedback and route alerts to a named reviewer without automatic
model promotion. UC09 Import assisted evidence: verify extracted fields and
suggested identities before using an authorised idempotent connector's results.

Requirements not yet implemented need new acceptance tests; traceability is a
plan, not a statement that every AT case has already passed. The separate research
branch records 45 unit tests; the pilot template review verified schema parity,
blank defaults and preservation of workbook controls. Neither establishes full UI,
security, integration, buyer or future-data acceptance. No new model evaluation is
performed while preparing this SRS.

## 11 Current evidence and staged delivery

| Capability | Evidence status | Remaining acceptance gap |
|---|---|---|
| Browser demo generation | Launcher reproduced; offline HTML exists | Full rendered browser flows and agreed compatibility/accessibility checks remain incomplete |
| Real quotation review | Local engine and fixture-based checks exist | Buyer source reconciliation, protected operations and user acceptance remain open |
| As-of history and split controls | Shared builder, corrected trainer and regression tests reproduced on development branches | Reviewed real-data adapter, true disclosure timestamps and buyer labels required |
| Synthetic model experiment | Accuracy 89.92%, precision 93.69%, recall 40.07% on the earlier fixed test; saved artifact verified | No real-world validation; no guarantee for a new target or buyer |
| Validation feature experiment | Recent-history candidate adds one detected delay at the same 32 false alerts | Too small and adaptively selected to justify replacing the current model |
| DataCo public research | 180,519 item rows across 65,752 orders; 28,965 provisional COMPLETE/CLOSED orders; cancellation/fraud and unresolved statuses separated | Historical shipping proxy with unverified availability, receipt and domain suitability; separate from buyer and synthetic data |
| DataCo validation comparison | 6,422 validation orders; shipping mode detects 1,994 delays with 265 false alerts; threshold-selected logistic detects 1,995 with 265 | One added detection is not a practical improvement claim; selected/measured on validation; final test remains unscored |
| Buyer data collection | Draft PR #1 reviewed at 335cdf7; 87-field blank pack with snapshot links, required cancellation events and related ignore rules | Still draft/unmerged; no buyer contacted, consent granted or real records supplied; native Excel and buyer export checks pending |
| Combined evidence pipeline | PR #4 tip 5d20b67: 57 unit tests and 21 artificial scenarios / 63 CLI runs passed | Draft stack unmerged; real buyer export, human label acceptance and operational validation pending |
| Modern feature roadmap | Draft PR #5 at a8f867a; ten phases and proposed feature checklist | Documentation only; selected libraries are not installed integrations |
| Recovery engine | Product direction and requirements only | Verified constraints, uncertainty, feasibility implementation and approval gates required |

Stage A exit: review this SRS, resolve requirement owners and maintain the regression
baseline. Stage B collection exit: approve pilot scope/access, reconcile a small
varied manual dry run and demonstrate protected storage/restore and buyer workflow.
Stage B automation exit, if implemented: validate the reviewed import mapping
before model use. Stage C exit: freeze a real target and costs,
collect mature evidence, compare baselines and obtain agreed future-period
evaluation results. Stage D exit: reconcile every proposed constraint and conduct
shadow recovery review without autonomous purchasing.

### Ten-phase release mapping

| Phase | Stage and requirement focus | Exit evidence |
|---|---|---|
| 1. Requirements and progress | A; FR44, NFR04/NFR14 | SRS/diagrams drafted and checked; owner/teacher review pending |
| 2. Evidence foundation | B; FR05, FR13, FR23-FR25 | Reviewed integration tests and separately authorised merges |
| 3. Buyer pilot | B; FR04/FR18/FR25 | Consent, protected evidence and human-reviewed outcomes |
| 4. Modern review interface | B; FR26-FR31 | Artificial browser tests and buyer workflow acceptance |
| 5. Reliable prediction | C; FR09-FR16/FR34 | Reproducible chronological comparison and frozen final evaluation |
| 6. Explanation/uncertainty | C; FR32-FR33 | Explanation correctness and calibration assessment |
| 7. Monitoring/feedback | B/C; FR35-FR37 | Repeated batches, reviewed feedback and mature-label evaluation |
| 8. Recovery | D; FR20-FR22/FR38-FR39 | Sourced constraints, solver checks and human shadow review |
| 9. Connectors/documents | B for this capability; FR40-FR41 | Permission, reviewed mappings and idempotence/failure checks |
| 10. Operation/extensions | B/C/D as applicable; FR42-FR45 | Hosting controls before hosting; separate extension acceptance |

The ten phases refine stages A-D; they do not postpone controls required for
earlier use. Local pilot access/storage/restore controls apply in phase 3.
Hosted access controls apply before any hosted private use, even if hosting is
started before phase 10. Phase 1 document preparation is not owner/teacher approval.

### Selected and conditional open-source components

| Component | Decision and capability | Gate |
|---|---|---|
| Mermaid | Selected for editable diagrams; not an application runtime requirement | Phase 1 rendering and accessible text |
| Plotly | Selected when current charts are insufficient | Phase 4 browser/offline/privacy compatibility |
| SHAP | Selected model-explanation candidate | Phase 6 model/schema/output compatibility |
| Evidently | Selected batch-monitoring candidate | Phase 7 real reference batches and delayed outcomes |
| OR-Tools | Selected recovery-optimisation candidate | Phase 8 sourced constraints, status and feasibility tests |
| MAPIE / Optuna / MLflow / DVC | Conditional uncertainty, search and experiment/data management | Demonstrated need and separate reviewed integration |
| RapidFuzz / Docling / Airbyte | Conditional matching, extraction and connectors | Buyer system selected; permission, source review and mappings |
| NetworkX / Leaflet / DuckDB | Conditional dependency analysis, maps and local analytics | Required relationships/location/scale justify adoption |
| Playwright / Hypothesis / Ruff | Conditional focused quality tools | Critical browser flows, invariants or static checks justify use |
| River / StatsForecast / Stockpyl | Optional later learning/planning modules | Separate approved target/data/evaluation specification |

Reuse existing Python domain checks, browser/CLI entry points and standard-library
capabilities first. Do not install all candidates together. Every adopted version
requires licence/attribution, maintenance, dependency and transmission review.
No selected library itself validates supplier claims or establishes buyer consent.

## 12 Assumptions decisions and references

### Open decisions

Confirm the first buyer/product/site, permission and storage owner, original
commitment source, date-only versus exact-time target, grace/returns/cancellation
rules, alert-review capacity, acceptable false-positive/false-negative cost,
evaluation maturity/cutoffs, browser/hardware matrix and release owner. Any future
teacher-specific submission sections can be added without inventing requirements
or changing evidence claims.

No new training, buyer outreach or purchase action should start merely because
this draft is prepared. The next specification gate is owner/academic review of
the scope and measurable requirements, followed by buyer review of collection
target, feasibility and approved use. Main and pilot PR approval remain separate.

Risks include incomplete timestamps, revised promises replacing originals,
misidentified supplier/product keys, missing open orders, inconsistent units,
selection bias and repeated validation reuse. Mitigate through versioned sources,
availability checks, exact identities, complete scoped exports, quarantine and
genuinely future evaluation. No universal data-volume minimum is asserted.

### Terms

PO means purchase order; an order line is one product/quantity/commitment within
a PO. RFQ means request for quotation. ML means machine learning. As-of features
use facts known at the decision time. A mature label is an outcome available
before the relevant learning/evaluation cutoff. Validation supports selection;
future evaluation estimates the frozen policy under its recorded protocol.

### Source material

This draft is grounded in repository records, not independent external validation.
The source snapshots are deliberately identified because the SRS branch does not
merge all source branches or include their datasets:

| Source snapshot | Material consulted | Use and limitation |
|---|---|---|
| main, 10acaaa | README and existing quotation/history/scenario modules | Existing prototype boundary; no production certification |
| earlier development, 52bbac4 | Corrected-trainer and synthetic validation reports; original collection plan | Synthetic baseline figures and initial requirements; not real-buyer validation |
| draft PR #1, 335cdf7 | PILOT-START.md, PLAN.md, blank workbook/CSVs and 87-field dictionary; re-review record | Manual pilot proposal, schema and corrected collection rules; unmerged, consent pending |
| research branch, 1ed1141 | DataCo SUITABILITY.md, baseline protocol and dataco-validation-thresholds.md | Separate public historical experiment; validation-only threshold selection, no deployment |

PR #1: https://github.com/kasanket64-prog/procurement-project/pull/1

All reported synthetic baseline test figures come from corrected-trainer.md;
later comparisons use validation only and did not rescore its final test. DataCo
source-wide suitability work inspected aggregate labels before its experiment;
its reserved test remains unscored but is not a pristine unseen source. No later
decision may disguise those limitations. Future requirement changes must record
reason, owner, affected FR/NFR IDs and acceptance evidence in project history.

### Modern component references

Official project references consulted for capability selection; these are not
dependency pins or promises of compatibility with this repository:

- Mermaid: https://mermaid.js.org/intro/
- Plotly: https://github.com/plotly/plotly.py
- SHAP: https://github.com/shap/shap
- Evidently: https://github.com/evidentlyai/evidently
- OR-Tools: https://github.com/google/or-tools
- MAPIE: https://github.com/scikit-learn-contrib/MAPIE

PR #4 combined evidence baseline: https://github.com/kasanket64-prog/procurement-project/pull/4
PR #5 roadmap baseline: https://github.com/kasanket64-prog/procurement-project/pull/5
Version 0.3 preserves earlier experiment figures as attributed historical results;
it does not rerun them or claim they validate the new features.

### Review record

Project owner review: pending. Academic guide review: pending. Buyer data and
operational approval: pending. Version 0.3 is a review draft and does not authorize
deployment, procurement actions, data collection or merging development work into main.
