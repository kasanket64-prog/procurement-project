# Phase 1 and Phase 2 technical re-review

17 November 2026. Related: issues #7 and #8. Technical evidence only; neither
phase is accepted, no reviewer signature is supplied, and no merge is authorized.

## Phase 1: completed technical preparation

Reviewed the SRS/architecture at `4afa82d9100d8b6d8097458f83b5f8c390bcad10`
(PR #6) and tracking/templates/worksheet at
`e6fe43167002b41bc0f7903bc4a8d6bb9eae5843` (PR #18). Local Python checks found:

- Ordered, unique FR01–FR45, NFR01–NFR15 and AT01–AT33. Every functional
  requirement has priority, acceptance information and acceptance traceability.
- All 14 local Markdown links across six documents resolved in their respective
  Git trees; table column counts were consistent.
- Three SVG previews parsed as XML without script elements. All authored Mermaid
  node labels matched the SVG text. The accepted-outcome cohort, separate
  recovery-constraint gate and calibration-before-freeze boundaries were retained.
- Both issue forms parsed with PyYAML 6.0.3 from existing temporary tooling,
  with unique field IDs, supported blocks, required input/privacy fields and ten
  correct phase-to-issue mappings. No runtime dependency was added.
- All 22 ordered approval criteria remain Pending. The PR template retains
  Related links and separate merge authority. Draft-template activation limits
  are stated. Static checks do not prove live GitHub form behavior.

Corrected stale roadmap progress in PR #6 at
`da1cad36870a2f83a1129ee6df318eda217b821a`: recorded board/template preparation,
separated delivered regression checks from integration acceptance, and recorded
partial Phase 4 work in PR #20. This does not mark later phases complete.
The tracking guide now includes PRs #20 and #21. The overlapping older roadmap
in PR #5 still needs a deliberate integration decision before any approved merge.

## Phase 1: still requires people

- Owner and teacher review of SRS/architecture, rubric, release scope and
  acceptance criteria using PHASE-1-APPROVAL.md. No actual decisions were provided.
- Agreement or explicit gated deferral of prediction target/policy, review
  capacity, acceptance metrics, browser/hardware targets and privacy boundaries.
- Human review of proposed issue/PR templates; activation needs a separately
  authorized default-branch merge. Live board settings must be rechecked at sign-off.

No fresh PDF rendering, Mermaid rendering, live workflow inspection/trigger test,
live form submission, full accessibility audit or buyer-data validation was done.
Earlier rendering/settings checks remain attributed to their original baselines.

## Phase 2: repeatable integrated verification

Re-ran combined PR #4 baseline
`5d20b673d39e0f78fdfb217a0f5cecb232e6714f`: **57 tests passed**.
Draft [PR #21](https://github.com/kasanket64-prog/procurement-project/pull/21)
at `fcf44c707724b7acb46a9f9ebd7a826d552fc15e` adds the earlier external
scenario matrix to normal unittest discovery without production-code changes:

```powershell
python -m unittest discover -s tests -v
python -m unittest discover -s tests -p test_buyer_pipeline_cli.py -v
```

**58 tests passed in 47.860 seconds**, comprising the 57 existing tests plus one
integration test with **21 scenario subtests / 63 subprocess executions**. The
focused integration run also passed. Windows / Python 3.12.14; child CLI clock
fixed at 14 November 2026, 12:00 UTC so artificial approval fixtures do not expire.
Actual CSV loading, validators, reconciliation and labeling run without mocks.
Tests cover expected blocked/successful exits and JSON, balances, labels, human
review/model-readiness boundaries, no fixture source-reference disclosure and
unchanged SHA-256 input-file manifests. Temporary artificial inputs were removed.

PR #21 documents the scenarios and command, including deliberate test-only
real/approved declarations. It is stacked on PR #4; earlier PR heads are unchanged.
Tests do not authenticate buyer permission, source truth, coverage or real outcomes.

## Phase 2: remaining gate

The technical repeatability task is delivered in a draft, not an approved release.
Review PRs #1–#4 and #21 as a stack; accept the evidence and dependencies; authorize
merges separately and rerun checks on any approved integrated revision. Do not
merge stacked changes into earlier draft feature branches. Genuine buyer workflow
validation and human label acceptance remain later gates. No CI success is claimed.

Main remains at `10acaaa48d3e47f7a39e37c8e140a1900bac21b9`.
