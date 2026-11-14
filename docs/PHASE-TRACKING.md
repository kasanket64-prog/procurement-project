# Phase tracking

[Live GitHub board](https://github.com/users/kasanket64-prog/projects/1).
The board is project metadata; it does not merge or modify main.

Use the [Phase 1 approval checklist](PHASE-1-APPROVAL.md) for separate owner and
teacher decisions on the SRS, diagrams, board and templates. Approval is pending
and does not authorise a merge or buyer-data use.

| Phase | Issue | Existing PRs | Phase gate |
|---|---|---|---|
| 01 Requirements and progress | #7 | #5, #6, #17, #18 | Awaiting owner/teacher review |
| 02 Evidence foundation | #8 | #1, #2, #3, #4 | Tested at combined draft tip; integration approval pending |
| 03 Consenting buyer pilot | #9 | #1 (preparation only) | Planned; consent and actual collection pending |
| 04 Modern review interface | #10 | None yet | Planned |
| 05 Reliable predictions | #11 | None yet | Planned acceptance gate; earlier experiments exist |
| 06 Explanations and uncertainty | #12 | None yet | Planned |
| 07 Monitoring and feedback | #13 | None yet | Planned |
| 08 Recovery planning | #14 | None yet | Planned |
| 09 Integrations and documents | #15 | None yet | Planned |
| 10 Secure operation and expansion | #16 | None yet | Planned |

Issue/PR numbers refer to kasanket64-prog/procurement-project. The phase issue
links back to its existing PRs; each PR links to its phase. Keep that mapping
current when adding work. Use Related links, not automatic whole-phase closure.

## Status rules

- Todo means the phase/task is planned; existing experiments may still exist.
- In Progress means active work; record what is still unverified.
- Awaiting review means draft implementation/documents exist, but approval or
  integration is pending. Record test evidence separately.
- Done means the item's own reviewed exit criteria are accepted; a PR merge
  alone does not complete a phase or establish buyer validation.
- Keep exact commit, tests, review, merge and buyer validation as separate facts.
  Leave phase issues open until the complete exit checklist is accepted.
- Keep local pilot protections ahead of real-data use, and hosting protections
  ahead of hosted private use, regardless of phase numbering.

## Live board workflows

Verified configuration on 14 November 2026. Project settings are live GitHub
metadata, separate from the template files in this branch.

| Workflow | State | Behaviour |
|---|---|---|
| Auto-close issue (131447642) | Disabled | Moving a card to Done must not automatically close its issue. |
| Item closed (131447637) | Disabled | Closing an issue or abandoning a PR must not count as accepted completion. |
| Pull request merged (131447639) | Disabled | A merge must not automatically satisfy review/phase acceptance. |
| Auto-add sub-issues to project (131447645) | Enabled | Adds sub-issues; does not accept an exit gate. |
| Item added to project (131447650) | Enabled | Sets new issue/PR cards to Todo. |
| Pull request linked to issue (131447648) | Enabled | Sets linked work to In Progress, not Done. |

All other project workflows are disabled at this verification. Default workflow
settings can change independently of Git history: recheck them after project
configuration changes. Before manually selecting Done or closing a phase, record
reviewer, accepted exit checklist and evidence in the phase issue. For abandoned,
duplicate or not-planned items, record the reason and archive the card if useful;
do not classify them as successfully Done. This board is an organisational aid,
not an approval-enforcement system. No workflow grants permission to merge.

Verification checked persisted settings after reload and the unchanged phase
cards. No real phase issue/PR was closed or merged to exercise a trigger.

## Using the templates before merge

The issue forms and PR template on this branch are reviewable drafts. GitHub
normally discovers repository templates from its default branch: they will not
automatically become the default creation forms while main remains unchanged.
Until separately approved and merged, copy the relevant template text into a
new issue/PR and link its phase issue manually. These files add no repository
workflow or auto-merge. The live project's retained intake/linking rules are
listed above; completion and closure remain manual after reviewed acceptance.

## Evidence and privacy

The roadmap/SRS baseline is in draft PR #6, not main. The combined buyer pipeline
at 5d20b67 passed 57 unit tests and 21 artificial end-to-end scenarios; this is
not real buyer validation. See #8 for the exit gate.

Never include buyer exports, filled templates, identity keys, credentials or
private attachments in issues, PRs or board cards. Use artificial reproductions.
The board and GitHub checklists organise work; they do not enforce data permission,
validate model quality or authorise purchasing or merges.
