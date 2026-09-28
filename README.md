# Procurement Platform

A PBL prototype for finding potential suppliers, exploring product descriptions and preparing quotation requests. One browser interface brings together synthetic supplier recommendations, real historical public supplier leads and public catalog entries.

**This is a research prototype, not a live marketplace.** Public leads do not establish current stock, prices, brand authorization or delivery capability. Synthetic recommendations are clearly labelled.

## Quick start: browser interface

Use Python 3.11 or newer and a modern browser. The browser launcher needs **no third-party Python packages**, account, server or API key.

```powershell
git clone https://github.com/kasanket64-prog/procurement-project.git
cd procurement-project
python ml/procurement_platform.py
```

Already downloaded the project? Open a terminal in that folder and run only the last command. If Windows recognizes `py` instead of `python`, use `py -3 ml/procurement_platform.py`.

If the browser does not open automatically, open the generated `ml/procurement_platform.html` file in your browser. You can also open the included HTML directly; rerun the launcher after updating local data to rebuild it.

### A five-minute walkthrough

1. Click **Try steel coil**. Select **China** and set the maximum demo unit-price figure to **900**. Click **Find suppliers & products** to see the demo ranking. These figures have no verified currency.
2. Click **Try microscope** to see companies associated with relevant historical public awards. Open an official notice to review the evidence.
3. Click **Try washer**, then **Use in quotation request** on CATMAT 275035. Review the source description and draft translation.
4. Enter quantity, purchasing unit, optional brand/model, destination, delivery date, timezone and quotation currency. Confirm the specifications, then review and download the request.

Nothing is sent to suppliers. Browser drafts are not saved automatically: download before closing the page. Editing a draft requires another review before downloading.

## What data is included?

| Source | Current scope | Use |
|---|---|---|
| Synthetic procurement history | Approximately 47,000 records; 516 supplier-product summaries and 50 products | Demonstration ranking and historical-risk experiments |
| UK Contracts Finder | 100 captured releases / 96 procurement processes / 248 source supplier identities | Historical company leads and official notice links |
| Brazil CATMAT | 40 catalog entries; five English draft translations | Product descriptions and source classifications |

Supplier identities are source identifiers, not independently verified legal entities. UK source coverage does not imply every supplier is located in the UK. The award sample is a bounded page, not global or representative market coverage. The application uses saved data, not live searches.

The synthetic history remains in `dataset/procurement.csv`; the 516-row summary used by the matcher is `dataset/supplier_items.csv`. A smaller summary does not mean the original history was discarded.

Public records, synthetic suppliers and catalogs are not joined by company name or treated as interchangeable quotations. Award totals are not unit prices. Historical maximum quantities are observations, not supplier capacity.

### Attribution and reuse

UK data: Contracts Finder, Cabinet Office. Contains public sector information licensed under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Capture details and hashes are in `dataset/public_procurement/contracts_finder_2025_sample/`.

CATMAT entries preserve Portuguese descriptions, source codes and evidence-file references. Dataset-specific reuse terms and independent translation review remain unresolved; use this portion as a local research pilot. Some evidence references name the original research workspace files, which are not all included in this repository.

No blanket licence is asserted for all repository data or code. Review source-specific terms before redistribution or commercial use.

## Optional terminal workflows

These tools are retained for features not yet available in the browser. Use Python 3.11 and optionally a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-terminal.txt
.\.venv\Scripts\python.exe ml/supplier_matcher.py
```

| Command (after installing dependencies) | Purpose |
|---|---|
| `python ml/supplier_matcher.py` | Combined supplier/catalog search and request preparation |
| `python ml/quotation_demo.py` | Fictional quotation comparison, budget/deadline scenarios and report export |
| `python ml/real_intake.py` | Prepare an RFQ or enter genuine supplier quotations |
| `python ml/catalog_search.py` | Dedicated CATMAT research search |
| `python ml/supplier_discovery.py` | Dedicated historical supplier browser and shortlist export |

If using the virtual environment, replace `python` in this table with `.\.venv\Scripts\python.exe`.

For the advanced semantic demo, also install the optional ML dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ml.txt
.\.venv\Scripts\python.exe ml/procurement_ai.py
```

The first semantic-model run may download `all-MiniLM-L6-v2` from Hugging Face. The current advanced demo uses a supplier-history risk baseline selected in synthetic evaluation. It does not establish real-world delivery-risk accuracy. The browser uses the original weighted matcher and does not run this semantic model or risk estimator.

Large legacy `.pkl` model files are intentionally excluded from Git. They remain on the development computer. The browser does not require them; older training or model-loading scripts may require additional dependencies and locally generated artifacts. The optional dependency lists are not a fully locked training environment.

## Genuine quotations and brand requirements

There are no genuine supplier quotations included. Never attest that demo records are genuine. Real intake supports explicit required/offered brand and model fields; missing information and exact mismatches block eligibility. Permitted alternatives remain pending buyer review and outside the eligible ranking.

The browser prepares request text only. It does not authenticate supplier claims, evaluate received quotations or verify branded-product availability. The real comparison engine remains a terminal workflow.

## Project layout

- `ml/procurement_platform.py` and `ml/procurement_platform_template.html`: main browser launcher and interface.
- `ml/supplier_matcher.py`: unified terminal matcher.
- `ml/real_intake.py`, `ml/real_procurement.py`: request entry and quotation checks.
- `ml/quotation_schema.py`, `ml/quotation_mapping.py`: schema and intake mapping audit.
- `dataset/`: synthetic history, summaries and public-award evidence.
- `ml/public_supplier_leads.json`, `ml/catmat_research_catalog.json`: source-labelled search snapshots.

Keep secrets, private quotations, local sessions, model binaries and backups out of commits using `.gitignore`.

## Current limits and next validation

- No live supplier-stock, price or delivery feed.
- No validated real-world delivery-risk model.
- Limited keyword search and English catalog coverage.
- Browser and terminal capabilities are not yet identical.
- No authentication, shared database, automatic supplier messaging or purchase execution.

The next validation is to observe buyers completing a search and RFQ, then compare actual supplier responses with permission. Expand public-source coverage while preserving provenance and distinguishing historical leads from current offers.
