# NOVA landing page

Open `ml/landing.html` locally, then select **Open workspace**. The workspace links back through **NOVA home**. The existing Python launcher continues opening the workspace directly.

Editable Figma desktop/mobile frames and foundations: https://www.figma.com/design/eK0wYoaTRimm1VoBAQR2SE?node-id=15-142

The page uses local HTML/CSS/JavaScript, reusable card/button styles, a 12-column desktop hero and responsive grids. CSS variables mirror Figma color and radius tokens. Inter is bundled under the adjacent SIL Open Font License. The glass sphere was generated with Figma AI and downloaded as an asset; it is not a live 3D model. Reduced-motion preferences disable ambient animation and pointer depth. No dependencies, analytics, signups, payments or data uploads are added.

Showcase tabs contain explicitly artificial examples, not live calculations or imported buyer data. Use the workspace for working What-If controls and evidence report previews. Recovery remains a separate local CLI prototype. Pilot testimonials, production claims and paid checkout are deliberately absent. NOVA is a visual concept name; trademark clearance has not been established.

Check interactions and local asset/link integrity with `node --test tests/test_landing.cjs tests/test_platform_what_if.cjs`.

Verified on 18 November 2026: all 14 Node checks passed, including tab click/keyboard navigation, reduced-motion listener gating, local asset/link integrity and existing workspace regressions. Generated workspace HTML was rebuilt from its template. Desktop Figma composition was visually reviewed; mobile clipping was repaired through auto-layout sizing and checked structurally. Final mobile visual review and native browser/device checks remain pending: Windows browser verification could not establish the current URL, and the in-app local-page preview timed out. These results are local checks, not CI, production acceptance or a completed accessibility audit.
