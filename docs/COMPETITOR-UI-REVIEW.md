# Procurement product references and next UI slice

Reviewed 18 November 2026. Public vendor descriptions are capability claims,
not independently tested performance. No paid product, authenticated dashboard
or end-to-end vendor demo was tested. Missing information below is not evidence
that a competitor lacks a feature. This review does not change the SRS or phase gates.

## Six-platform comparison

| Platform and official source | Documented overlap | Our current position | Useful direction |
|---|---|---|---|
| [o9](https://o9solutions.com/) | Forecasting, inventory, supplier risk/collaboration and scenario analysis | Synthetic What-If prototype; no accepted demand/inventory forecasting | Compare scenarios at a fixed baseline; expose planning assumptions |
| [SAP spend management](https://www.sap.com/products/spend-management.html) | Supplier lifecycle, sourcing, buying, invoices, approvals and compliance | Discovery/RFQ and local quote-review prototypes; no operational source-to-pay suite | Separate evidence review, sourcing and human decisions |
| [Coupa dashboard documentation](https://docs.coupa.com/en/supplier-documentation/coupa-for-suppliers/the-coupa-supplier-portal-or-csp/features-and-processes-in-the-coupa-supplier-portal/dashboards-in-the-csp) | Supplier-portal invoice/PO/receivable dashboards; separate [workflow documentation](https://compass.coupa.com/en-us/products/product-documentation/total-spend-management-platform/workflows-and-approvals/process-automator/process-automator-actions) covers automation | No invoice/payment/receivable workflow; no genuine spend dashboard | Scope, currency and denominator must accompany every future metric |
| [Blue Yonder planning](https://blueyonder.com/solutions/supply-chain-planning) | Demand/supply planning, inventory, what-if tradeoffs and constraint-aware planning | No validated inventory optimizer, live supply network or capacity model | Show constraints and unavailable evidence before recommendations |
| [Kinaxis Maestro](https://www.kinaxis.com/en/blog/introducing-kinaxis-maestro-platform) | Scenario modeling, integrated planning and orchestration | Local independent scenarios and evidence reports, no collaborative orchestration | Stable scenario identity, clear baseline/changed inputs and tradeoffs |
| [GEP SMART](https://www.gep.com/clp/gep-smart/procurement-software) | Spend analysis, sourcing, PO processing and invoice management; [unified platform](https://www.gep.com/innovation/unified-procurement-platform) describes supplier/contracts workflows | Local prototypes and draft evidence tooling, no operational workflow automation | Consistent navigation and a clear next action across modules |

Coupa homepage/product retrieval returned 403; its dashboard result was available
in the search index but opening redirected to an unsupported-browser page. The
indexed scope is supplier-portal dashboards, not proof of its buyer dashboard UI.
GEP's main SMART URL also returned 403; alternate official pages supplied the
capability descriptions. No private dashboard screenshots were inspected or copied.

Feature-by-feature gaps in our project:

| Capability | Verified current slice | Remaining acceptance/work |
|---|---|---|
| Supplier discovery and quotations | Prototype discovery/RFQ and local quotation engine | Buyer source reconciliation, current offers and operational workflow |
| Scenario analysis | Independent synthetic What-If inputs and budget behavior tested | Real revised quotations, supported constraints and buyer comparison |
| Evidence quality and history | Draft readiness/schema previews and correction/reversal timeline | Promise events, quarantine/review decisions, controlled exports |
| Forecasting/inventory | Experiments are not accepted product capabilities | Separate approved target/data and evaluation; no forecasting claims |
| Supplier performance/risk | Synthetic examples and unaccepted experiments | Scoped denominators, mature accepted labels, chronological evaluation |
| Approvals, invoices and payment | Human decisions remain outside the app | No automatic buying/payment; real workflows need separate authorization |
| Hosting/integrations | Offline local prototype | Access controls, connectors, restore/rollback and operational validation |

## Working UI direction

These are our design choices, inferred from workflow needs rather than copied
vendor layouts. Blue Yonder's [published UX strategy](https://blueyonder.com/why-blue-yonder/user-experience)
also emphasizes clarity, explanation and accessibility; it is not a verified UI audit.

1. Keep one consistent workspace with direct entry points for requirements,
   evidence review and synthetic scenario inputs. Links must target existing screens.
2. Use compact headers and progressive disclosure. Preserve detailed evidence
   behind keyboard-accessible disclosures, rather than filling every card with text.
3. Show actual imported counts and provenance. Until genuine denominators exist,
   display no invented savings, risk, spend or delivery-success dashboard metrics.
4. Keep synthetic results, public leads and private evidence clearly distinguished.
5. Add supplier scorecards and a human-review queue only when their underlying
   counts and decisions are implemented. Charts must have matching table totals.

Implemented in this slice: responsive workspace-section navigation, a more compact
header and the existing integrated timeline/evidence UI. No vendor branding,
artwork, proprietary layouts or runtime dependencies are copied. Figma remains
optional; the working HTML/CSS is the editable design and implementation together.

## Differentiation hypotheses to measure

These are research candidates, not established market gaps or novel inventions.

| Candidate | Existing foundation | Experiment needed |
|---|---|---|
| Decision-time replay that preserves transcription corrections and receipt reversals | Shared availability/lineage gates and synthetic invariance tests | Compare naive latest-row joins with cutoff-aware replay on independently reviewed cases; measure leakage violations, wrong labels, replay agreement, time/memory |
| Evidence-limited scenario comparison | Stable supplier IDs, original request and fixed total budget tests | Compare assumptions made by naive scenarios versus source-supported comparisons; measure unsupported claims, eligible-set errors and reviewer resolution time |
| Auditable, constraint-supported recovery | Requirements only | Establish real sourced offers/capacity, compare against a declared baseline; measure feasibility violations, cost/service outcomes and unresolved constraints |

Current tests establish behavior on artificial cases, not better prediction,
buyer value or superiority over any listed vendor. No new model was trained and
no proprietary product was benchmarked for this review.

## Preliminary patent screen

The broad combination of AI, procurement, scenarios and traceability is not a
defensible novelty claim. [WIPO](https://www.wipo.int/en/web/patents/faq_patents)
explains that software patentability also depends on eligible subject matter,
novelty, inventive step and industrial applicability, with jurisdiction-specific
rules. [IP India](https://ipindia.gov.in/pages/patents/learn/basics-of-patents/which-inventions-can-be-patented)
also describes novelty, inventive step and industrial application criteria.

A limited public patent search used `procurement provenance` and
`supply chain bitemporal` on Google Patents. Relevant adjacent disclosures found:

- [US20210149365A1 — Product procurement with automated qualification](https://patents.google.com/patent/US20210149365A1/en): procurement with verifiable provenance and automated product qualification.
- [US8713073 — Management of temporal data by means of a canonical schema](https://patents.google.com/patent/US8713073): temporal metadata and integrity constraints, including bitemporal data.
- [US11275726B1 — Distributed data processing with complete provenance and reproducibility](https://patents.google.com/patent/US11275726B1/en): provenance/reproducibility using bitemporal event records.

Only abstracts/descriptions/search excerpts were screened, not claims or patent
families. No legal status, infringement, freedom-to-operate or novelty conclusion
is established. Patent potential is **undetermined**. Before a filing claim,
define the exact technical mechanism and measurable effect, search patent and
non-patent literature, compare each proposed claim with the closest disclosures,
and obtain jurisdiction-specific professional review. A polished dashboard or a
feature list alone does not establish patentability.
