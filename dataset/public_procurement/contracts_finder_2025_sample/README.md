# Real public procurement dataset

Source: UK Contracts Finder, Cabinet Office.
Contains public sector information licensed under the Open Government Licence v3.0.
Declared licence: http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/

Downloaded 100 award-notice releases representing 96 procurement processes and 248 distinct source supplier IDs.
Categories: {'services': 69, 'goods': 17, 'works': 14}.
Notice publication range: 2025-12-30T13:37:03Z to 2025-12-31T18:06:56Z.
One page from a 2025 query. More pages exist; this is not a representative market sample.

## Files

- `raw_releases.json`: captured source response.
- `manifest.json`: request URL, capture time, source licence and source-file SHA-256.
- `discovery_records.json`: descriptions, classifications, buyers, awards and suppliers with source IDs and notice links.
- `quality_report.json`: field coverage and duplicate/process counts.

## What this supports

Historical supplier discovery, real procurement-description search and classification research. Supplier country cannot be inferred from the UK source jurisdiction.

## What it does not establish

Award totals are not unit prices or current quotations. Multiple suppliers can share an award; do not allocate the full award value to each. Revisions to a procurement process remain separate releases, not extra purchases. Dates and status are preserved.
No verified order-level promised-versus-actual delivery labels were established. No supplier capacity, current stock, or risk probability can be inferred. Records must not be joined to synthetic suppliers by name.
Raw records are retained for audit; the discovery export omits party contact/address details. Source descriptions can still contain public contact information. Assess licence exclusions and intended use before redistribution.

| Field | Releases containing it |
|---|---:|
| description | 100/100 |
| structured_quantity | 0/100 |
| structured_unit_price | 0/100 |
| contract_implementation | 0/100 |
| award_value_and_currency | 100/100 |

## Example records

- [Contract award for WCM ECC Supervisor, Technical Support and ECoW](https://www.contractsfinder.service.gov.uk/Notice/f8cab55d-90a5-4f7a-87d4-1ed0f5bd8bef) — services
- [Robotic Process Automation for Humber Health Partnership Administration Services](https://www.contractsfinder.service.gov.uk/Notice/e0b6fde2-2738-4fc6-8ee8-8d316b8f674a) — services
- [LAS IUC Strategy](https://www.contractsfinder.service.gov.uk/Notice/71800951-05e4-4431-9ae8-37f76518603f) — services
- [36718 Carrisbrooke](https://www.contractsfinder.service.gov.uk/Notice/b60ed20b-ae6f-4cc9-90f8-70ffcad4ad3b) — services
- [36717 - Leicester Partnership School (Carrisbrooke)](https://www.contractsfinder.service.gov.uk/Notice/69b6fe8e-e0b3-420f-adab-fde1ce0ed6b1) — services
- [Adult Social Care Case Management System - Paris Extension (Civica Care Records)](https://www.contractsfinder.service.gov.uk/Notice/86088ae9-dc7e-4fe6-ac90-a06d6f855a20) — goods
- [SEN15458](https://www.contractsfinder.service.gov.uk/Notice/26bad879-211a-4ccb-b3d2-d7be46917e68) — services
- [The Kent Health Visiting Service](https://www.contractsfinder.service.gov.uk/Notice/125bbda5-6571-4595-86d3-4a53f3c5e464) — services
- [Holborn Refurbishment works to Custody suite including ESS works](https://www.contractsfinder.service.gov.uk/Notice/0ba72421-d918-441c-b5ee-50d8f69fde06) — works
- [LAS Demand and Capacity Review](https://www.contractsfinder.service.gov.uk/Notice/a97d5b8d-2773-4b68-b1f1-a2425c5a9fd4) — services
- [LAS Ambulance Funding Model](https://www.contractsfinder.service.gov.uk/Notice/e518d91c-6945-4a3b-ab85-3fdf6387b7ce) — services
- [LAS Power Platform Strategy](https://www.contractsfinder.service.gov.uk/Notice/561f7450-c648-4998-8037-f3cb5a11dd09) — services
