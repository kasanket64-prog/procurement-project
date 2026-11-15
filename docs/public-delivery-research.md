# Public delivery-data research — 15 November 2026

## Usable research evidence

The historical **SCMS Delivery History / Supply Chain Shipment Pricing** dataset contains scheduled and recorded delivery dates, vendor labels and procurement line items. A downloaded public mirror has **10,324 line items, 33 columns and 43 destination countries**. Recorded client deliveries span **2 May 2006 to 14 September 2015**. This is actual-outcome research attributed to the USAID program, not independently certified buyer evidence for this app.

The original USAID download failed to resolve during this session. The primary Global Fund PQR transaction-report link returned an error. Consequently, analysis uses a disclosed third-party mirror, not an asserted fresh official export.

- Claimed original publisher: USAID, Supply Chain Management System / Supply Chain Shipment Pricing, portal ID `a3rc-nmf6`.
- Original URL attempted: https://data.usaid.gov/api/views/a3rc-nmf6/rows.csv?accessType=DOWNLOAD
- Mirror: https://github.com/jrcinco/supply-chain-shipment-price-data/blob/3d12aa307c4fcfa19df7dfbfa2f277db9132c557/SCMS_Delivery_History_Dataset.csv
- Retrieved: 15 November 2026. Exact input SHA-256 and analyzer digest are recorded in [the analysis JSON](public-delivery-analysis.json).
- Metadata evidence: https://data.amerigeoss.org/dataset/supply-chain-shipment-pricing-data (search-indexed metadata; direct fetch unavailable). It identifies USAID and both a CC BY-ND licence URL and a CC-BY rights statement. These conflicting terms are unresolved. No blanket public-domain claim is made. Raw data and row-level derivatives are not added to this repository or customer-facing app.

## Results and accounting

Late means the recorded **Delivered to Client Date** is later than **Scheduled Delivery Date**, with no grace period. These are descriptive comparisons, not estimates of supplier fault or model accuracy.

| Population | Eligible count | Late count | Late share |
|---|---:|---:|---:|
| Procurement line items | 10,324 | 1,186 | 11.49% |
| ASN/DN identifier groups with consistent scheduled and actual dates | 7,020 | 798 | 11.37% |

There are **7,030 distinct ASN/DN identifiers**, so line items must not be described as independent shipments. Ten identifier groups have conflicting date pairs and are excluded from the grouped rate. No rows lack a parseable scheduled or actual delivery date. Three rows record the delivery before its actual delivery date; they remain visible as a quality issue and are not a source of feature-availability evidence.

ASN/DN identifiers are grouping keys; they do not prove complete independent physical shipments. Schedule revisions are not observed. Neither the initial promised date nor reliable historical availability timestamps are established. A late comparison can reflect buyer, route, customs or schedule changes, not just vendor behavior. No supplier names are ranked or joined to app leads.

## Reproduce locally

Download the exact CSV from the pinned mirror above, then run:

```text
python ml/analyze_public_deliveries.py PATH_TO_CSV --output docs/public-delivery-analysis.json
python -m unittest discover -s tests -p "test_public_deliveries.py" -v
```

The analyzer rejects files whose byte digest differs from the reviewed snapshot. CI tests accounting and date edge cases with controlled fixtures; it does not download or certify the external CSV. The full dataset analysis was run locally, and its summary is committed for review.

## Other sources checked

- [Global Fund PQR](https://www.theglobalfund.org/en/sourcing-management/price-quality-reporting/) documents public health-product procurement, but its linked transaction report failed during this session. Do not claim its data were downloaded.
- [DataCo V5](https://data.mendeley.com/datasets/8gx2fvg2k6/5), by Constante, Silva and Pereira, is published under CC BY 4.0 and describes clothing, sports and electronics supply-chain data. It is a retail research candidate, not proof about app supplier delivery outcomes. No DataCo performance claim is imported.

## Product boundary

This finding supports development of real-date ingestion and descriptive analysis. It does not remove existing release gates for authentic supplier prediction. No trained model, current supplier score, capacity, inventory, quotation or purchase authorization was added. Customer-facing demo comparisons remain labeled; previous audit and model limitations remain intact. The next useful step is to resolve the source authenticity and reuse evidence, then evaluate data availability and generalization before any predictive integration.
