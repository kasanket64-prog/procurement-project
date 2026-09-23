# Start the multi-country quotation pilot

You do not need to edit JSON files. Buyers and suppliers can be in any country. Choose the currency and destination timezone for each request. Open PowerShell and run:

```powershell
cd C:\Users\Sanket\AI-Supply-Chain
python ml\real_intake.py
```

Choose **1 Prepare a supplier quotation request** if you do not have offers yet. Enter the destination timezone, product, exact specification, quantity, unit, destination, required delivery date, currency and internal budget. Review the generated request and save it. Your internal budget is not included in the supplier request.

The program prints the saved folder location under `real-pilot\sessions`. Open `supplier_request.md`, fill in any buyer contact details you want suppliers to use, and send it yourself to suppliers. Nothing is sent automatically. Use the same specification and destination for every supplier. Ask for written confirmation of any missing price, validity or delivery terms; do not guess them.

Choose **2 Enter genuine quotations and compare** once you have written offers. Keep original documents available. The guided questions collect quote dates, expiry, quantity, units, currency, total, destination and commercial confirmations. Enter times as `YYYY-MM-DD HH:MM` in the selected destination timezone, or copy an ISO timestamp with an explicit UTC offset from the source. Ambiguous or nonexistent local times during daylight-saving changes require clarification. If the supplier provides no precise expiry or delivery terms, request clarification before trying to create a complete comparison.

Example timezone/currency pairs: `Asia/Kolkata` / `INR`, `America/New_York` / `USD`, `Europe/Berlin` / `EUR`, and `Asia/Tokyo` / `JPY`. These are examples, not an allowed-country list. Choose the actual destination zone, especially in countries with several timezones. Enter a three-letter currency code agreed with the supplier; the tool checks code format, not membership in an official currency registry. Different currencies are excluded from cost ranking; automatic exchange-rate conversion is not implemented.

Reuse the same supplier ID for repeat offers from the same company. Record the supplier's actual quote number and revision. Retain only the applicable version of an offer for a decision; the tool does not resolve document revisions for you. Confirmation questions require an explicit yes or no; a missing confirmation never becomes approval.

After saving, open `comparison.txt` for the readable result. `input.json` and `review.json` retain the entered evidence and result. Each session has its own folder, so earlier sessions remain available. If a save fails, inspect the reported partial-session location before retrying; there is no transactional database yet.

Type `cancel` at any question to stop before saving. This does not delete earlier sessions. This is a local pilot with no accounts or protected shared storage; use it only on a controlled computer with records you are authorized to process.

An eligible quote meets the checked conditions; it is not independently authenticated or automatically recommended as the best supplier. Cost ranking does not assess warranty, payment or service differences. Real delivery-risk prediction remains unavailable until genuine outcomes are evaluated. No purchase is authorized by this tool.
