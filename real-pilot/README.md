# Multi-country procurement pilot — documented quotations

## Current status

A local quotation-review engine is implemented and tested. No real records have been supplied, no real-world risk model has been validated, and this is not a production deployment. The existing synthetic application remains a demonstration. This pilot does not send orders, pay suppliers or choose a supplier automatically.

The first practical use is to compare documented quotes for one precisely specified product, quantity and destination in any country. Each request selects its own currency and destination timezone. Start with a buyer you can work with and two or three written quotations for the same requirement. This is a practical pilot size, not a model-training minimum. Obtain permission before using business records. No messages have been sent to buyers or suppliers.

## What to collect first

| Evidence | Required information |
|---|---|
| Buyer requirement | Exact product and specifications, quantity and purchasing unit, destination, destination timezone, delivery deadline, total budget and currency |
| Supplier | Stable internal ID, name, country, source document reference |
| Quote | Quote ID/version, supplier/product IDs, exact quantity and unit, total and currency, destination, promised delivery date, issue/receipt/expiry timestamps |
| Commercial review | Confirmation that specifications match and total includes all applicable tax, freight and duties; reference to payment, warranty, delivery and other terms |
| Provenance | Source reference, permission to use records, reviewer identifier and review timestamp |

Keep original documents in a protected local folder. Use internal IDs instead of copying bank details, personal phone numbers or unrelated personal data into this tool. Source references can identify those local documents; the engine never opens or downloads them. An operator declaring a source real does not independently establish authenticity.

## Run a review

Use the guided `ml/real_intake.py` tool, or complete a copy of `global_input_template.json` using genuine documents. `india_input_template.json` remains an optional India example. Blank/default values deliberately fail validation. Add supplier and quote objects as needed. Set `data_kind` to `real` and permission/confirmation flags to true only after verification. Do not relabel generated examples as real.

From the installed project directory:

```powershell
python ml\real_procurement.py real-pilot\my_request.json --output real-pilot\review-001.json
```

The supplied template is not `my_request.json`; create your completed copy first. Use a new report filename for each review. In the workspace version, run `python real_procurement.py <input-file> --output <new-report-file>`.

Amounts and quantities are decimal strings without commas, for example `"12500.50"`. The supported input range is up to 18 integer digits and six decimal places. Currency must be three uppercase ASCII letters, such as INR, USD or EUR. Format is validated; official currency membership and currency-specific rounding are not checked. Dates use `YYYY-MM-DD`. Event timestamps include an offset, for example `2026-09-23T14:30:00+05:30`. Choose genuine dates rather than copying this illustration. Delivery dates are evaluated in `request.decision_timezone`, an IANA name such as `Asia/Kolkata`, `Europe/London` or `America/New_York`. Quote expiry is checked at the actual decision instant. Legacy INR inputs without the new timezone field retain Asia/Kolkata and the report labels that assumption; other requests require an explicit zone. Blank timezone fields are rejected.

Timezone data is available on the current computer. On another Windows installation, install the pilot requirements if named zones cannot be loaded. Python uses system timezone data or its `tzdata` package; see the [Python timezone documentation](https://docs.python.org/3/library/zoneinfo.html). Local intake times that occur twice during clock changes require an explicit source offset; nonexistent local times are rejected.

IDs are exact, case-sensitive keys, not product-name guesses. Purchasing units must match exactly. No automatic currency, unit or pack conversion is performed. A different quote quantity requires a revised quote; the system does not assume the same price applies at another quantity. Multiple versions of the same source quote must be resolved before comparison.

The total is the documented amount payable for that exact quantity and destination. The tool does not calculate tax rates, validate tax compliance or infer missing charges. Human reviewers must inspect the referenced terms, including payment and warranty differences that are not ranked automatically.

## Output and controls

- Missing identities, inconsistent timestamps, invalid amounts, unauthorized or declared synthetic sources block review.
- Expired/unavailable quotes and commercial mismatches are listed with reasons and receive no cost rank.
- Eligible quotes receive a cost rank using exact decimal arithmetic; equal totals tie. This is cost ranking, not an overall supplier-quality score.
- Risk stays unavailable. The synthetic prior and Random Forest are never loaded.
- Reports record input and engine hashes plus decision time. Existing report files cannot be overwritten by the command. Hashes support traceability, but these ordinary local files are not a signed or tamper-proof audit store.
- The output never authorizes a purchase. A buyer must review the original documents and make the decision.

## Data sources

Seek genuine quotations and historical order records from a consenting buyer in your target country. Public procurement portals may provide requirements and awards, but these are not automatically supplier offers to your buyer or observed delivery outcomes. India remains one example: the [Central Public Procurement Portal](https://eprocure.gov.in/epublish/app?component=%24DirectLink&page=Home) publishes tender enquiries, corrigenda and contract-award details. Confirm access/reuse terms before bulk collection; no scraping or redistribution permission was established here.

For delivery-risk evaluation, work with a consenting buyer to obtain stable order-line and supplier IDs, product specifications, original and revised promise dates with revision timestamps, quantities, units, currency, placed/received timestamps, partial deliveries, actual completion, cancellations and timestamps when outcomes became available. Preserve open orders; do not label them on time. Historical prices need transaction dates and terms. Do not merge public award names with supplier records based only on similar names.

## Gates before real-world release

1. Obtain real records and verify source rights, identities, units and completeness with the buyer.
2. Run the pilot alongside the buyer's existing process. Reconcile every eligibility result and amount to the original documents; investigate all disagreements.
3. Define prediction target and decision use with the buyer. Evaluate chronological baselines on genuine outcomes, including uncertainty, calibration and performance for new suppliers. Agree acceptance thresholds before final evaluation. There is no defensible universal minimum number of orders.
4. Add a reviewed interface and operational controls: access permissions, protected storage, backups and restore tests, versioned input/quote revisions, error monitoring, dependency review and user acceptance testing.
5. Release only the capabilities supported by the pilot evidence. Keep purchasing approval with the buyer; do not describe cost ranking as validated supplier risk.

These gates remain open. Existing synthetic evaluations and the new fixture-based software tests do not validate real supplier performance.
