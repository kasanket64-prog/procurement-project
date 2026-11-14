# Phase tracking

[Live GitHub board](https://github.com/users/kasanket64-prog/projects/1).
The board is project metadata; it does not merge or modify main.

| Phase | Issue | Existing PRs | Phase gate |
|---|---|---|---|
| 01 Requirements and progress | #7 | #5, #6 | Awaiting owner/teacher review |
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

## Using the templates before merge

The issue forms and PR template on this branch are reviewable drafts. GitHub
normally discovers repository templates from its default branch: they will not
automatically become the default creation forms while main remains unchanged.
Until separately approved and merged, copy the relevant template text into a
new issue/PR and link its phase issue manually. No workflow or auto-merge is enabled
by this change. Review project workflows before relying on automated status changes.

## Evidence and privacy

The roadmap/SRS baseline is in draft PR #6, not main. The combined buyer pipeline
at 5d20b67 passed 57 unit tests and 21 artificial end-to-end scenarios; this is
not real buyer validation. See #8 for the exit gate.

Never include buyer exports, filled templates, identity keys, credentials or
private attachments in issues, PRs or board cards. Use artificial reproductions.
The board and GitHub checklists organise work; they do not enforce data permission,
validate model quality or authorise purchasing or merges.
