# Phase 1 approval checklist and acceptance criteria

Prepared 14 November 2026. **Review draft: no approval recorded.**
For the project owner and teacher/academic guide. Use this checklist to accept
the requirements and planning baseline; it does not certify a working modern
platform, grant buyer-data permission or authorise a merge.

## 1. Review pack and version control

| Material | Review baseline | What to open |
|---|---|---|
| SRS v0.3, PDF and architecture | PR #6, `4afa82d9100d8b6d8097458f83b5f8c390bcad10` | [SRS](https://github.com/kasanket64-prog/procurement-project/blob/4afa82d9100d8b6d8097458f83b5f8c390bcad10/docs/SRS.md), [PDF](https://github.com/kasanket64-prog/procurement-project/blob/4afa82d9100d8b6d8097458f83b5f8c390bcad10/docs/SRS.pdf), [architecture](https://github.com/kasanket64-prog/procurement-project/blob/4afa82d9100d8b6d8097458f83b5f8c390bcad10/docs/ARCHITECTURE.md) |
| Ten-phase roadmap | PR #6 progress reconciliation at `da1cad36870a2f83a1129ee6df318eda217b821a`; SRS unchanged; earlier PR #5 overlaps | [Roadmap](https://github.com/kasanket64-prog/procurement-project/blob/da1cad36870a2f83a1129ee6df318eda217b821a/ROADMAP.md) |
| Tracking guide | PR #18, `1a905f6504c71bc0ab206113a167f00cae0055e6` | [Guide including the checklist link and PR #18 phase index](https://github.com/kasanket64-prog/procurement-project/blob/1a905f6504c71bc0ab206113a167f00cae0055e6/docs/PHASE-TRACKING.md) |
| Issue and PR templates | PR #17, `92d0120081d4b8a0bae8e20ee516cb22412df0a7` | [Issue forms](https://github.com/kasanket64-prog/procurement-project/tree/92d0120081d4b8a0bae8e20ee516cb22412df0a7/.github/ISSUE_TEMPLATE), [PR template](https://github.com/kasanket64-prog/procurement-project/blob/92d0120081d4b8a0bae8e20ee516cb22412df0a7/.github/PULL_REQUEST_TEMPLATE.md) |
| Live phase board | Not versioned by Git; recheck at sign-off | [Board](https://github.com/users/kasanket64-prog/projects/1), [phase-1 issue #7](https://github.com/kasanket64-prog/procurement-project/issues/7) |

Record the actual reviewed commits, date and any newer revisions below. A later
change to scope, targets, evidence boundaries or approval controls requires review
of the affected criteria. Existing technical reviews are supporting evidence,
not signatures from the owner or teacher. The PR #18 checklist and tracking-guide
changes are part of this review pack, alongside the separately pinned PR #17
templates; record the actual checklist revision in the sign-off record.

## 2. How to record a decision

For every criterion record **Pass**, **Changes required**, or **Pending**, plus an
evidence reference or requested change. All rows start Pending. A deferral must
name the decision owner and the future gate that blocks use until it is resolved.
Do not mark a criterion Pass merely because code or a document exists.

The owner reviews product scope and practical priorities. The teacher reviews
academic scope, required format and evaluation expectations. Neither review grants
permission to use a buyer's records; that requires separate buyer approval.

## 3. Acceptance worksheet

| ID | Review item | Observable pass condition | Reviewer | Decision / evidence |
|---|---|---|---|---|
| P1-01 | Problem and users | Reviewer can explain the procurement problem, intended users and decision being supported from the SRS. | Both | Pending |
| P1-02 | Scope and academic requirements | Initial release, later features and exclusions are agreed. Teacher format, rubric, required sections and submission deliverables are recorded or explicitly confirmed as not prescribed. | Both | Pending |
| P1-03 | Current versus planned work | Prototype, tested branch work, planned features, merged work and buyer validation are distinguished; no synthetic accuracy is presented as real-world evidence. | Both | Pending |
| P1-04 | Requirement completeness | SRS contains unique FR01-FR45, NFR01-NFR15 and AT01-AT33; every functional requirement links to an acceptance scenario and its release gate. Check quality as well as numbering. | Both | Pending |
| P1-05 | Prediction target and timing | Original supplier promise, order-release decision time, full accepted quantity, local date boundary, open/unknown/cancelled cases and outcome availability are understandable. Any buyer-specific variations are explicitly gated. | Owner; teacher reviews method | Pending |
| P1-06 | No leakage and honest evaluation | Training, calibration, validation and final-evaluation roles are distinct. All fitted postprocessing/thresholds freeze before final testing; later fitted changes require fresh future evaluation. | Both | Pending |
| P1-07 | Nonfunctional criteria | Integrity, privacy, accessibility, reproducibility and performance criteria have an intended verification method. Proposed hardware/browser/performance targets are approved or assigned a blocking decision gate. | Both | Pending |
| P1-08 | System architecture | Browser/CLI use shared validation; existing local foundations and planned modules are distinguished; training is separate from user inference. No automatic purchasing path exists. | Both | Pending |
| P1-09 | Evidence-to-label diagram | Original evidence/corrections, receipt reconciliation, coverage/policy checks, label proposals and human acceptance appear in the correct order; proposals alone are not model-ready. | Both | Pending |
| P1-10 | Accepted-outcome path | Human-accepted, cutoff-mature outcomes reach supervised evaluation/monitoring through the controlled cohort, and never enter decision-time inference features. | Both | Pending |
| P1-11 | Model-release diagram | Optional non-test calibration and validation precede full-pipeline freeze and final evaluation; unsuitable results stop release; later feedback cannot auto-promote models. | Both | Pending |
| P1-12 | Recovery constraints | Recovery takes separately validated offers/buyer constraints as well as predictions. Missing/stale and infeasible cases are distinct; human purchasing authority remains intact. | Both | Pending |
| P1-13 | Diagram/document consistency | Mermaid, SVG previews, PDF and SRS describe the same boundaries and gates. All three diagrams and the PDF are readable; captions disclose planned status. | Both | Pending |
| P1-14 | Phase order | All ten phases match the roadmap. Local-data protections precede collection, hosting controls precede hosted private use, and phase 6 cannot tune against phase 5's final test. | Both | Pending |
| P1-15 | Phase and PR links | Phases 1-10 map to issues #7-#16. Phase 1 includes PRs #5/#6/#17/#18; phase 2 includes #1-#4; #1 supports phase-3 preparation only. Links resolve in both directions. | Owner | Pending |
| P1-16 | Board completion safeguards | Auto-close issue, Item closed -> Done and Pull request merged -> Done remain disabled. Retained rules cannot accept an exit gate. Done/closure needs recorded human review and evidence. | Owner; teacher reviews meaning | Pending |
| P1-17 | Accurate progress | Phases with pending approvals remain open. Reconcile older roadmap checkboxes with the live board/issue #7; board/templates being prepared does not mean approved or active defaults. | Owner | Pending |
| P1-18 | Issue forms | Phase-task and defect forms require phase/requirements, acceptance or reproduction evidence, and privacy confirmation. All ten phase options point to the correct issues. | Both | Pending |
| P1-19 | PR template | Template requests scope, phase links, exact checks/results, limitations and data safeguards. Related links avoid automatic whole-phase closure; merge remains a separate decision. | Both | Pending |
| P1-20 | Template activation limits | Reviewers understand that branch-only templates are drafts; default forms normally require an approved default-branch merge. Static YAML checks do not prove live form submission. | Owner | Pending |
| P1-21 | Privacy and authority | Pack contains no buyer records, filled templates, credentials or identity maps. Consent, retention and protected storage are later buyer gates; ignore rules are not access control. | Both | Pending |
| P1-22 | Open decisions and next scope | Every unresolved decision has an owner and blocking gate. The next task is explicitly scoped; no blanket approval of later features, data collection, deployment or merge is inferred. | Both | Pending |

## 4. Decisions to agree or explicitly defer

Fill in values; do not infer agreement from suggested defaults in the SRS.

| Decision | Value / rationale | Accountable owner | Must be resolved before |
|---|---|---|---|
| Teacher rubric, required SRS format and deliverables | Pending | Teacher | Academic baseline approval |
| Initial release boundaries and next small task | Pending | Project owner | Product baseline approval / next implementation |
| Buyer/site/product family, permission and retention | Pending | Pilot owner + consenting buyer | Real collection or processing |
| Original promise source, date/time precision, grace, cancellations and returns | Pending | Buyer + pilot owner | Buyer labels or cohort use |
| Buyer review workload, false-alert/missed-delay costs and acceptance metrics | Pending | Buyer + evaluator | Real-model selection/release |
| Calibration/selection partitions, label maturity and untouched future evaluation | Pending | Evaluator + owner | Any relevant training/selection |
| Browser/hardware matrix and benchmark targets | Pending | Owner; teacher for academic expectations | Relevant UI/performance acceptance |
| Hosting scope, access/storage, restore and rollback responsibilities | Pending | Owner/operator | Corresponding real-data use or hosted operation |

The historical DataCo limit of 265 false alerts belongs to its original validation
set; it is not a buyer workload target. The SRS's proposed performance figures
are not measured benchmarks. Buyer-specific metrics may remain deferred at phase 1
only if the reviewer accepts the named blocking gates above. No universal minimum
training sample or promised model accuracy is established by this checklist.

## 5. Known verification and remaining limits

The [17 November technical re-review](PHASE-1-2-REVIEW.md) records new structural
checks and Phase 2 regression results. It is supporting evidence only; all 22
worksheet decisions and both sign-offs remain pending.

- Prior technical checks at the pinned SRS baseline found 45 FR, 15 NFR and
  33 AT identifiers, 13 valid local links and three parseable/rendered Mermaid
  diagrams. The 22-page PDF was rendered and reviewed. These are document checks.
- Prior template review at the pinned tracking baseline passed YAML/mapping
  checks. The three automatic completion/closure rules were confirmed disabled
  in saved settings. Recheck live settings at sign-off because Git cannot freeze them.
- The combined pipeline at 5d20b67 passed 57 unit tests and 21 artificial scenarios.
  This is phase-2 technical evidence, not a phase-1 production/model acceptance test.
- Live form submissions and workflow triggers have not been exercised. No genuine
  buyer outcome, hosted security deployment or real-world model quality is validated.
- PR #5 and PR #6 overlap documentation; reconcile shared files in a separately
  approved integration plan. This checklist does not authorise that merge.

## 6. Change requests

| Criterion ID | Requested correction / reason | Responsible person | Evidence / due date | Disposition |
|---|---|---|---|---|
| Pending | None recorded by reviewers yet | Pending | Pending | Pending |

Record dates when agreed; this document creates no deadline. Resolve blocking
changes before approval. Nonblocking deferrals require a rationale and named gate.

## 7. Independent sign-off record

| Review field | Project owner | Teacher / academic guide |
|---|---|---|
| Reviewer name | Not provided | Not provided |
| Review date | Pending | Pending |
| SRS/diagram commit reviewed | Pending | Pending |
| Tracking/template commit and board review date | Pending | Pending |
| Checklist revision reviewed | Pending | Pending |
| Decision: Approved / Changes required / Pending | Pending | Pending |
| Criterion IDs passed / requiring changes | Pending | Pending |
| Accepted deferrals and blocking gates | Pending | Pending |
| Evidence reference or recorded acknowledgement | Pending | Pending |

Phase 1 can be recorded as accepted only after both reviewers record explicit
decisions, required criteria pass, blocking corrections are resolved and approved
deferrals have owners/gates. Record acceptance in issue #7 without closing it
automatically. Do not treat a GitHub technical re-review as either signature.

**Phase approval is not merge permission.** Keep main unchanged and all PRs
unmerged until a separate explicit merge instruction. No buyer outreach, data use,
purchase, deployment or automatic implementation of the full roadmap is authorised
by signing this requirements/planning checklist.
