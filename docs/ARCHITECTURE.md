# Architecture views - SRS v0.3

Proposed logical design, 14 November 2026. These diagrams are not a claim of
deployed services or completed integrations. Shared local domain functions and
the existing browser/CLI remain the starting point. See [SRS](SRS.md) and
[roadmap](../ROADMAP.md) for requirement IDs, release gates and evidence status.

The SVG previews and Mermaid blocks below are generated from the same node/edge
definitions. Solid arrows indicate intended data/control flow, not network APIs.
Human approval and permission are required controls, not declarations the system can authenticate by itself.

## 1. System components and authority boundaries

Proposed logical architecture. Existing Python and offline browser foundations remain; adapters, review UI, monitoring and recovery are planned. Permissioned buyer files stay outside Git. Shared rules serve browser and CLI. Training is a separate activity; no component places purchases. Source-kind separation is required before downstream use.

![System components and authority boundaries](diagrams/system.svg)

```mermaid
flowchart TD
    buyer["Buyer / reviewer<br/>Human authority"]
    sources["Buyer files / later adapters<br/>Permissioned; outside Git"]
    demo["Synthetic / public sources<br/>Separate evidence kind"]
    ui["Browser / CLI adapters<br/>Existing + planned UI"]
    gate["Permission / schema / time<br/>Shared validation gate"]
    store["Segregated evidence<br/>Protected versioned storage"]
    quotes["Quotation review<br/>Existing domain foundation"]
    labels["Receipts / label proposals<br/>Draft tested foundation"]
    features["As-of feature builder<br/>Decision-time facts only"]
    review["Evidence / label review<br/>Human acceptance gate"]
    risk["Prediction + explanation<br/>Later model acceptance"]
    monitor["Evaluation / monitoring<br/>Separate controlled activity"]
    decision["Buyer decision outside app<br/>No automatic purchasing"]
    recovery["Recovery comparison<br/>Later sourced constraints"]
    registry["Reviewed model manifest<br/>Trusted inference artifact"]
    buyer --> ui
    ui --> gate
    sources --> gate
    demo --> gate
    gate --> store
    gate -->|"validated"| quotes
    store --> labels
    store --> features
    quotes --> review
    labels --> review
    features --> monitor
    features --> risk
    registry --> risk
    risk --> recovery
    recovery --> decision
    review --> decision
    monitor -->|"reviewed release"| registry
```

## 2. Evidence intake, receipts and human label acceptance

Intended evidence workflow using the draft tested snapshot/receipt/label foundation. Lineage, provenance and timing are checked across all historical versions; business values are checked on active snapshots. Receipt coverage and an approved label policy gate any binary proposal. Human acceptance and a separate controlled adapter are required before an accepted outcome enters a learning cohort. Outcome labels never enter decision-time predictors.

![Evidence intake, receipts and human label acceptance](diagrams/evidence-flow.svg)

```mermaid
flowchart TD
    input["Permissioned source batch<br/>Immutable original evidence"]
    history["History / permission checks<br/>Identity, timing, lineage"]
    blocked["Blocked / quarantined<br/>Reason + source reference"]
    active["Resolve active snapshots<br/>Validate business values"]
    events["Receipts + coverage review<br/>Sourced event history"]
    reconcile["Reconcile accepted quantity<br/>Partial / rejected / reversed"]
    policy["Approved label policy<br/>Original promise / local date"]
    proposal["Outcome proposal<br/>Pending / unknown / cancelled<br/>or evidenced on-time / late"]
    review["Human label acceptance<br/>Proposal alone not model-ready"]
    cohort["Controlled cohort adapter<br/>Accepted mature labels only"]
    input --> history
    history -->|"invalid"| blocked
    history -->|"valid"| active
    active -->|"invalid"| blocked
    active -->|"valid"| reconcile
    events --> reconcile
    reconcile --> proposal
    policy --> proposal
    proposal --> review
    review -->|"accepted + validated"| cohort
```

## 3. Chronological evaluation and controlled model release

Proposed model governance. Freeze the target/cohort and decision-time features; fit transforms and models on training only. Select models and alert thresholds on validation only. Freeze the candidate before the final evaluation; an unsuitable result is reported honestly, and the same test is not recycled for tuning. Only an authorised release reaches inference. Drift or feedback cannot automatically promote a model. Calibration, if used, needs its own suitable partition and protocol.

![Chronological evaluation and controlled model release](diagrams/model-release.svg)

```mermaid
flowchart TD
    cohort["Approved cohort / target<br/>Decision-time features + labels"]
    split["Chronological partitions<br/>Mature labels at each cutoff"]
    train["Training only<br/>Fit transforms + candidates"]
    validation["Validation only<br/>Select model + threshold"]
    test["Reserved final period<br/>No selection access"]
    freeze["Freeze candidate + policy<br/>Data / code / model manifest"]
    evaluate["Controlled final evaluation<br/>Report success or failure"]
    release["Authorised release gate<br/>Reviewed metrics + rollback"]
    report["If unsuitable: report / stop<br/>Fresh future test for new work"]
    inference["Trusted inference + explanation<br/>No training on user request"]
    monitor["Monitor + human feedback<br/>Review future candidates only"]
    cohort --> split
    split --> train
    split --> validation
    split -->|"reserved"| test
    train -->|"candidates"| validation
    validation --> freeze
    freeze --> evaluate
    test -->|"once frozen"| evaluate
    evaluate -->|"acceptable"| release
    evaluate -->|"unsuitable"| report
    release --> inference
    inference --> monitor
```

## Reading the boundaries

- Raw buyer files and identity maps are protected outside Git; synthetic/public evidence remains segregated.
- Browser and CLI must call the same shared rules; an adapter cannot bypass validation.
- A proposed label is not human acceptance and is not model-ready.
- Model explanations describe model behaviour; recovery scenarios are conditional, not causal promises.
- Final-test results cannot feed the same selection loop. Fresh work needs a fresh evaluation protocol.
- Drift, subjective ratings and extracted document text do not establish ground truth.
- No arrow authorises an order, payment, supplier message or automatic model deployment.
