# ProcureAI frontend handoff

## Working website
Open ml/procurement_platform.html locally. Edit ml/procurement_platform_template.html and rebuild with python ml/procurement_platform.py. The standalone interface includes the landing page, dashboard, requirement search, supplier discovery, supplier comparison, RFQ drafting and download, quote review, scenario calculator, analytics, dataset inventory, local settings and catalog assistant. Browser acceptance testing is pending.

## Planned design
Use a permanent desktop sidebar, mobile drawer, shared record header and requirement ID throughout the buyer workflow. Primary desktop frames and their purpose:

1. Landing — explain sourcing and open the workspace or sample journey.
2. Dashboard — reopen drafts and review outstanding work.
3. Requirements register — filter, duplicate and resume saved requirements.
4. Requirement editor — specifications, quantity, unit, destination, delivery, budget and currency.
5. Requirement detail — versions, evidence, shortlist and linked RFQs.
6. Discovery — search and filter supplier evidence, preserving source labels.
7. Supplier detail — matched products, evidence and missing details.
8. Shortlist comparison — inspect supplier differences and choose recipients.
9. RFQ register — find prepared requests and response counts.
10. RFQ details editor — freeze requested specifications and commercial terms.
11. Recipients and preview — review the document before downloading.
12. RFQ tracking — record pending, declined and received responses.
13. Quote entry — enter price, units, taxes, freight, validity and revision.
14. Quote validation — reconcile missing costs, specification changes and validity.
15. Offer comparison — compare eligible totals in the same currency and units.
16. Decision review — capture selected offer, exceptions and rationale.
17. Decision history — reopen the decision with its original evidence.
18. Analytics — derive metrics from labeled datasets and inspect underlying rows.
19. What-if — change assumptions while keeping the original quote intact.
20. Dataset inventory — show provenance, record counts and sample fields.
21. Import review — map fields, preview valid and rejected rows before commitment.
22. Settings — currency, purchasing unit, timezone and comparison defaults.
23. Assistant — explain supported local lookup and link to evidence.
24. Help — contextual workflow explanations and scoring definitions.

## Premium landing page
Use Inter, background #050816, violet #8B5CF6, cyan #06B6D4, white text and subtle pink accents. At 1440 px use a 12-column grid, 80 px margins and 24 px gutters. Design 768 px and 390 px variants. Use reusable components and Auto Layout in Figma. Combine a floating glass sphere, aurora light, restrained particles, frosted surfaces and a holographic quote comparison. Provide reduced-motion and keyboard variants.

Section order: sticky navigation, hero, verified customer logos or buyer roles, features, interactive product showcase, approved testimonials, actual pricing or demo access, FAQ and footer. Primary action opens workspace. Showcase switches between requirement, discovery, comparison and review.

## Acceptance
For 100 units, A at INR 100 plus INR 1,500 freight totals INR 11,500. B at INR 108 with freight included totals INR 10,800. Reduce A freight to INR 500 and its total becomes INR 10,500. Unknown freight must leave the final total unresolved. Verify drafts, quote revisions, mobile layout, keyboard flow, missing evidence and error recovery before release.

## Research references
- [SAP Guided Sourcing](https://help.sap.com/docs/strategic-sourcing/managing-events-with-guided-sourcing/guided-sourcing-event-features)
- [Odoo alternative RFQs](https://www.odoo.com/documentation/17.0/applications/inventory_and_mrp/purchase/manage_deals/calls_for_tenders.html)
- [Oracle sourcing terminology](https://docs.oracle.com/en/cloud/saas/procurement/26a/fainp/src-terminology.html)
