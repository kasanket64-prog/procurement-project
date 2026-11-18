# Evidence-aware supplier replacement prototype

18 November 2026. Experimental early Phase 8 slice, not accepted recovery/AI
capability. The earlier roadmap and buyer gates remain in force. User requested
this focused artificial disruption-to-proposal experiment; no real pilot begins.

## Supported workflow

1. Supply the existing quotation bundle plus a sourced, explicitly confirmed
   `supplier_unavailable` event. Event time <= known time <= decision time.
2. Reuse `real_procurement.evaluate` for quote permission/provenance, as-of
   availability, exact product/quantity/unit/currency/destination, full costs,
   budget, brand and delivery-commitment checks. No revised prices are inferred.
3. Exclude the disrupted supplier. Require a per-quote capacity declaration with
   a source record, positive validity interval, matching unit, confirmation,
   availability at the decision time and enough documented available quantity.
4. Separate excluded, unavailable and infeasible offers. Missing/unconfirmed,
   future-known/stale capacity or unverified mappings cannot become feasible.
5. Propose all equal lowest documented totals among feasible full-quantity offers.
   Show source references, delivery commitment, cost and unresolved reasons in
   read-only HTML/JSON for human review. Never purchase, train or contact anyone.

The result is deterministic decision support, **not AI prediction**, a delivery
guarantee, authenticated stock or a reservation. Risk remains unavailable.
Source declarations do not establish actual authenticity or capacity. Confirm
every commercial fact with the source before any external action.

## Input additions

Use existing `real-pilot/global_input_template.json` quotation fields. Additional
top-level fields below are illustrative placeholders, not approved working data:

```json
{
  "recovery_event": {
    "type": "supplier_unavailable", "confirmed": false,
    "supplier_id": "", "source_id": "", "source_record_id": "",
    "event_at": "", "known_at": ""
  },
  "capacity_evidence": [{
    "quote_id": "", "source_id": "", "source_record_id": "",
    "confirmed": false, "quantity": "", "unit": "",
    "known_at": "", "valid_until": ""
  }]
}
```

All source IDs must already exist in the bundle. Capacity quote/source-record
duplicates and malformed fields block the whole report. Decimal strings preserve
exact costs/quantities. Capacity zero is valid evidence of insufficient quantity.
Default flags remain false; change declarations only with actual reviewed evidence.

```powershell
python ml/procurement_recovery.py "C:\BuyerApprovedStorage\replacement-input.json"
python ml/procurement_recovery.py "C:\BuyerApprovedStorage\replacement-input.json" --format json
```

Use `--demo` only for exclusively synthetic source declarations. Default mode
retains existing declared-real/permission gates; this development used artificial
data exclusively. Exit 0 means options available; exit 2 means blocked, evidence
review needed or infeasible. HTML/JSON go to stdout; no file writes or network.
Shell redirection may overwrite a destination: use a new private filename.
Reports include a canonical input SHA-256; this is a content identifier, not proof
of authenticity or an engine-version manifest. Genuine reports remain private.

## Reproducible artificial benchmark

Run `python -m unittest discover -s tests -p test_procurement_recovery.py -v`.
The test compares the proposal engine with an explicitly limited **price-only
ablation**: same existing commercial eligibility and disrupted-supplier exclusion,
but no capacity gate. This is not an implementation or benchmark of a competitor.

| Constructed case | Price-only selection | Evidence-aware result |
|---|---|---|
| Complete evidence | quote-2 | quote-2 |
| Cheapest capacity missing | quote-2 | quote-3 |
| Cheapest capacity insufficient | quote-2 | quote-3 |
| Cheapest capacity expired | quote-2 | quote-3 |
| All alternative capacity missing | quote-2 | No proposal; needs review |
| All alternatives exceed budget | None | No proposal; infeasible |

On these six designed cases, price-only selects an unsupported/insufficient
capacity offer in four cases. The proposal engine selects a feasible offer in
four and abstains in two; no selected offer violates these fixture constraints.
This is a functional stress test showing the effect of the added evidence gate,
not a representative sample, statistical result, measured buyer saving, better
forecast accuracy or real-world recovery improvement. Price-only already obeys
quote budget/deadline checks; it is not a deliberately broken quote validator.

## Limits and next gate

Only whole-quantity replacement for a declared unavailable supplier is supported.
No automatic disruption detection, price-increase/shortage event model, split
allocation, multi-site optimization, capacity sharing across simultaneous orders,
live stock, risk model, causal lead-time estimate or solver is implemented.
HTML is a separate review screen; the workspace evidence reader does not accept
this report. No stored buyer approval or outcome-feedback workflow exists.
These remain pending rather than being simulated as genuine acceptance.

Before operational use: buyer-reviewed input mappings and evidence validity,
concurrent capacity/reservation rules, versioned decision/approval/outcome records,
source authentication, real-data benchmarks and human acceptance. No novelty,
patentability or superiority over SAP/o9/Coupa/Kinaxis/GEP/Blue Yonder is claimed.
