# UI acceptance checklist

18 November 2026. Phase 4 remains **in progress**, not accepted. This checklist distinguishes automated evidence, design checks and pending browser acceptance. It does not authorize merging or using buyer data.

## Verified baseline

- Landing implementation: draft PR #31; recovery CLI: draft #30. Both remain stacked on earlier drafts, unmerged.
- App-code baseline `0e21ae4`: 15 Node landing/workspace checks passed. They cover tab click/keyboard behavior in a simulated DOM, motion-listener gating, local links/assets, primary-action contrast, workspace evidence readers and What-If regressions.
- Earlier head `3a1bf93`: full Python suite passed 93 tests in 93.095 seconds. Later changes were CSS/tests/documentation and Figma; no newer full Python result is claimed.
- Figma: action colors synchronized, mobile card clipping repaired, then narrow button/FAQ labels and dashboard text widths repaired. Final structural readback confirmed content-width buttons at 40px height. Final visual confirmation is pending because the Starter MCP quota was reached.
- Main remains `10acaaa48d3e47f7a39e37c8e140a1900bac21b9`. No production readiness, CI result, real-buyer acceptance or prediction accuracy is established.

## Browser acceptance still to perform

Use exclusively artificial fixtures. Record browser/version, viewport in CSS pixels, zoom, exact commit, test case and observed result. A working file link or simulated DOM assertion is not browser evidence.

| Case | Action | Expected result | Status |
| --- | --- | --- | --- |
| Desktop landing | Open `ml/landing.html` at 1440px, 100% zoom | Local font/sphere load; no clipped headings, overlapping controls or horizontal page scrolling | Pending |
| Mobile landing | Inspect at 390px and 320px | Navigation, CTAs, cards, tabs, FAQ and footer fit; text remains readable and controls reachable | Pending |
| Keyboard | Tab from the top; activate skip link, CTAs, tabs and FAQ | Visible focus; skip reaches main content; tab arrows/Home/End change selection and focus; Enter/Space toggle FAQ | Pending |
| Showcase | Select Evidence, Scenarios and Recovery | Correct title, metrics and offer text; one selected tab; synthetic-data boundary stays visible | Pending |
| Workspace round trip | Select Open workspace, then NOVA home | Working generated workspace opens and home returns to the landing page | Pending |
| Reflow | Inspect at browser-confirmed 200% zoom | Content wraps; no lost controls or clipped text; sticky navigation does not hide focused content | Pending |
| Motion | With reduced motion already configured, inspect page | No sphere float or pointer depth; controls remain usable | Pending |
| Local assets | Open offline without altering network/security settings | Bundled font/image load; page remains usable without external requests | Pending |
| Workspace regressions | Search, adjust What-If inputs and import/clear artificial evidence | Existing controls remain usable; original request preserved; clearing removes imported cards; no upload or purchase occurs | Partial historical evidence; current integrated head pending |

Current blockers: native Edge has a network sign-in modal; in-app local-file navigation is blocked by Browser Use URL policy and localhost preview timed out. Do not bypass security settings or infer a pass. Resume these checks when an allowed preview is available.

## Phase 4 scope still pending

See [Phase 4 issue #10](https://github.com/kasanket64-prog/procurement-project/issues/10) for the requirement map. Report preview and timelines are partial implementations; row quarantine/reviewed mappings, promise-event history, scoped supplier outcome counts with unknown/pending/cancelled separation, human review decisions/reasons, controlled exports and chart/table parity remain pending. Landing polish does not complete these workflow requirements.

Owner/buyer/academic acceptance is separate from passing checks. Keep drafts unmerged and genuine data outside GitHub. Do not assign a completion percentage without agreed scope and acceptance weights.
