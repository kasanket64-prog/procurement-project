"""Procurement recommendations and independent What-If simulations.

Run from the existing AI-Supply-Chain project root, or put this file in ml/.
Uses the Phase B supplier-history baseline by default; never trains a model.
Budgets distinguish unit-price ceilings from total line budgets.
Delivery and quantity cannot change observed historical risk: the source data has
no verified delivery commitment or capacity. Historical order size is only
an observation. Ranking remains based on the weighted supplier match score.
"""
from datetime import datetime
from pathlib import Path
from copy import deepcopy
import math
import re
if __name__ == '__main__':
    # On Windows initialize Torch DLLs before NumPy/scikit-learn dependencies.
    import torch
import pandas as pd
import joblib
from procurement_risk import SupplierHistoryRisk
from procurement_search import ProductSearch, select_product


def validate_request(request):
    for field in ("quantity", "delivery_days", "max_price"):
        value = request[field]
        if field == "max_price" and value is None:
            continue
        if value is None or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{field} must be a finite positive number.")
    if int(request["delivery_days"]) != request["delivery_days"]:
        raise ValueError("Delivery days must be a whole number.")
    total = request.get("total_budget")
    if total is not None and (not math.isfinite(total) or total <= 0):
        raise ValueError("Total budget must be a finite positive number.")
    weights = [request[k] for k in WEIGHT_NAMES]
    if any(not math.isfinite(w) or w < 0 for w in weights) or not math.isclose(sum(weights), 1):
        raise ValueError("Buyer priorities must be nonnegative and sum to 1.")


def unit_budget(request):
    """Derived ceiling: changing quantity preserves any original total budget."""
    limits = [request['max_price']] if request['max_price'] is not None else []
    if request.get('total_budget') is not None:
        limits.append(request['total_budget'] / request['quantity'])
    return min(limits) if limits else None


def scoring_reference(supplier_items, request):
    """Use the product/country population before budget or quote eligibility."""
    if request.get('scoring_reference') is not None:
        return request['scoring_reference']
    reference = supplier_items[supplier_items['item'] == request['product']]
    if request['country']:
        reference = reference[reference['supplier_country'].str.casefold() == request['country'].casefold()]
    return {'max_orders': float(reference['historical_orders'].max()) if not reference.empty else 0,
            'min_price': float(reference['avg_unit_price'].min()) if not reference.empty else 0}


def commercial_options(risk_model):
    """Read known categories from the fitted encoder without fitting anything."""
    if isinstance(risk_model, SupplierHistoryRisk):
        return risk_model.options
    preprocessor = risk_model.named_steps["preprocessor"]
    for name, transformer, columns in preprocessor.transformers_:
        if name == "categorical":
            return {
                field: [str(value) for value in transformer.categories_[list(columns).index(field)]]
                for field in ("business_unit", "payment_terms")
            }
    raise ValueError("The saved model has no categorical input encoder.")


def read_category(label, options):
    print(f"\n{label}:")
    for number, option in enumerate(options, 1):
        print(f"  {number}. {option}")
    while True:
        answer = input("Enter an option number or its name: ").strip()
        if answer.isascii() and answer.isdecimal() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1]
        for option in options:
            if answer.casefold() == option.casefold() or (
                    option.startswith('Net ') and answer == option.removeprefix('Net ')):
                return option
        print("Please select one of the listed options.")


def collect_commercial_inputs(request, risk_model):
    """Explicit buyer choices replace the former silent model-input defaults."""
    result = deepcopy(request)
    options = commercial_options(risk_model)
    print("\nORDER DETAILS — choose the values for this procurement request.")
    result["business_unit"] = read_category("Business unit", options["business_unit"])
    result["payment_terms"] = read_category("Payment terms", options["payment_terms"])
    while True:
        answer = input("Is this order on contract? (yes/no): ").strip().lower()
        if answer in ("yes", "y", "no", "n"):
            result["on_contract"] = int(answer in ("yes", "y"))
            break
        print("Please enter yes or no.")
    print("\nConfirmed order details:")
    print("Business unit:", result["business_unit"])
    print("Payment terms:", result["payment_terms"])
    print("On contract:", "Yes" if result["on_contract"] else "No")
    print("These order details apply to all suppliers and remain fixed in What-If simulations.")
    return result


def validate_commercial_inputs(request, risk_model):
    for field, options in commercial_options(risk_model).items():
        if request.get(field) not in options:
            raise ValueError(f"Select a supported {field} before predicting risk.")
    if request.get("on_contract") not in (0, 1):
        raise ValueError("Contract status must be explicitly provided as 0 or 1.")


def simulate(original_request, field, value, supplier_items, supplier_history,
             risk_model, today):
    """Change one logical input on a private copy of the original request."""
    request = deepcopy(original_request)
    if field == "priorities":
        request.update(zip(WEIGHT_NAMES, PRIORITY_PRESETS[value]))
    elif field in ("max_price", "total_budget", "delivery_days", "quantity"):
        request[field] = value
    else:
        raise ValueError("Unknown simulation variable.")
    return request, recommend_suppliers(
        supplier_items, supplier_history, risk_model, request, today
    )


def compare_results(original, what_if):
    """Compare every eligible supplier using its ID and product, not its name."""
    keys = ["supplier_id", "item"]
    columns = keys + ["supplier_name", "rank", "match_score", "ai_late_risk"]
    comparison = original[columns].merge(
        what_if[columns], on=keys, how="outer",
        suffixes=("_original", "_what_if"), validate="one_to_one"
    )
    rows = []
    for _, row in comparison.iterrows():
        old, new = row["rank_original"], row["rank_what_if"]
        if pd.isna(new):
            change = "REMOVED: historical price exceeds what-if budget"
        elif pd.isna(old):
            change = "NEWLY ELIGIBLE"
        else:
            delta = int(old - new)
            change = f"Up {delta}" if delta > 0 else f"Down {-delta}" if delta < 0 else "Unchanged"
        name = row["supplier_name_original"]
        if pd.isna(name):
            name = row["supplier_name_what_if"]
        rows.append({
            "Supplier": name, "Supplier ID": row["supplier_id"],
            "Original rank": "N/A" if pd.isna(old) else int(old),
            "What-if rank": "N/A" if pd.isna(new) else int(new),
            "Original match %": row["match_score_original"],
            "What-if match %": row["match_score_what_if"],
            "Original risk %": row["ai_late_risk_original"],
            "What-if risk %": row["ai_late_risk_what_if"],
            "Rank change": change,
        })
    return pd.DataFrame(rows)


def read_number(prompt, whole=False, allow_any=False):
    while True:
        text = input(prompt).strip()
        if allow_any and text.lower() == "any":
            return None
        try:
            value = parse_number(text)
            if not math.isfinite(value) or value <= 0 or (whole and not value.is_integer()):
                raise ValueError
            return int(value) if whole else value
        except ValueError:
            print("Enter a positive whole number." if whole else "Enter a finite positive number.")


def what_if_loop(original_request, original_results, supplier_items,
                 supplier_history, risk_model, today):
    print("\nEach simulation changes one input from the ORIGINAL request.")
    print("Quantity uses the confirmed catalog unit. Total budgets stay fixed when quantity changes.")
    if isinstance(risk_model, SupplierHistoryRisk):
        print('Risk uses completed supplier history at the fixed decision date.')
        print('Changing price, quantity, deadline or priorities does not change those past outcomes.')
    else:
        print("AI risk changes are experimental model responses, not proven effects on delivery.")
    print('Verified supplier lead-time/capacity constraints are unavailable for historical recommendations.')
    while True:
        print("\n1 Change Budget\n2 Change Delivery Days\n3 Change Quantity\n4 Change Buyer Priorities\n5 Exit\n6 Compare Supplier Quotations")
        choice = input("Choose: ").strip()
        if choice == "5":
            return
        if choice == "6":
            quotation_session(original_request, supplier_items, supplier_history, risk_model, today)
            continue
        if choice == "1":
            field = 'total_budget' if original_request.get('total_budget') is not None else 'max_price'
            label = 'Total line budget' if field == 'total_budget' else 'Maximum unit price'
            value = read_number(f"{label} (or 'any'): ", allow_any=True)
        elif choice == "2":
            field, value = "delivery_days", read_number("Required delivery days: ", whole=True)
        elif choice == "3":
            field, value = "quantity", read_number("Required quantity: ")
        elif choice == "4":
            names = list(PRIORITY_PRESETS)
            print("\n1 Delivery\n2 Quality\n3 Price\n4 Experience")
            selection = input("Priority: ").strip()
            if selection not in ("1", "2", "3", "4"):
                print("Select a priority from 1 to 4.")
                continue
            field, value = "priorities", names[int(selection) - 1]
        else:
            print("Select an option from 1 to 6.")
            continue
        request, results = simulate(original_request, field, value, supplier_items,
                                    supplier_history, risk_model, today)
        print("\nORIGINAL vs WHAT-IF")
        if field == "priorities":
            print("Priorities (Delivery, Quality, Experience, Price):")
            print(tuple(original_request[k] for k in WEIGHT_NAMES), "->",
                  tuple(request[k] for k in WEIGHT_NAMES))
        else:
            print(f"{field}: {original_request[field]} -> {request[field]}")
        comparison = compare_results(original_results, results)
        if comparison.empty:
            print("No suppliers are eligible in either scenario.")
        else:
            print(comparison.to_string(index=False, na_rep="N/A", float_format=lambda n: f"{n:.2f}"))
        print("N/A means ineligible in that scenario; removed suppliers are not scored.")
        print("Risk is reported separately; ranks use the weighted match score.")
        display_recommendations(results, request)

PRIORITY_PRESETS = {
    "Delivery": (0.50, 0.25, 0.10, 0.15),
    "Quality": (0.20, 0.50, 0.15, 0.15),
    "Price": (0.20, 0.20, 0.10, 0.50),
    "Experience": (0.20, 0.20, 0.50, 0.10),
}
WEIGHT_NAMES = ("delivery_weight", "quality_weight", "experience_weight", "price_weight")

NUMBER = r'(?<![\w.,+-])(?:\d+(?:,\d+)*(?:\.\d+)?)(?!\d|[.,]\d)'
UNIT = r'(?:kilograms?|kgs?|tonnes?|tons?|pieces?|units?|each|packs?|boxes?|drums?|cases?)'


def parse_number(text):
    """Accept plain, western-grouped and Indian-grouped positive numbers."""
    if not re.fullmatch(r'(?:\d+|\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})+,\d{3})(?:\.\d+)?', text):
        raise ValueError('Invalid number or comma grouping.')
    value = float(text.replace(',', ''))
    if not math.isfinite(value) or value <= 0:
        raise ValueError('Enter a finite positive number.')
    return value


def canonical_unit(value):
    value = (value or '').lower()
    if re.fullmatch(r'kg|kgs|kilograms?', value):
        return 'kg'
    if re.fullmatch(r'tons?|tonnes?', value):
        return 'ton'
    if value in ('piece', 'pieces', 'unit', 'units', 'each'):
        return 'each'
    return value.rstrip('s') or None


def extract_requirements(requirement, countries=()):
    text_lower = requirement.lower()
    quantity = None
    issues = []
    quantity_unit = None
    quantity_patterns = [rf'\b(?:need|quantity\s*(?:of|:)?|order|buy)\s*({NUMBER})(?:\s*({UNIT})\b)?',
                         rf'({NUMBER})\s*({UNIT})\b']
    for pattern in quantity_patterns:
        match = re.search(pattern, text_lower)
        if match:
            try:
                quantity = parse_number(match.group(1))
            except ValueError:
                issues.append('Quantity has invalid numeric formatting; enter it again.')
            quantity_unit = canonical_unit(match.group(2))
            break
    country = None
    country_map = {name.lower(): name for name in countries}
    country_map.update({'china': 'China', 'india': 'India', 'japan': 'Japan', 'germany': 'Germany',
                       'united states': 'USA', 'usa': 'USA', 'united kingdom': 'UK', 'uk': 'UK',
                       'france': 'France', 'italy': 'Italy', 'south korea': 'South Korea',
                       'singapore': 'Singapore', 'canada': 'Canada', 'mexico': 'Mexico',
                       'vietnam': 'Vietnam', 'poland': 'Poland', 'brazil': 'Brazil', 'australia': 'Australia'})
    found_countries = []
    for country_name in sorted(country_map, key=len, reverse=True):
        if re.search('\\b' + re.escape(country_name) + '\\b', text_lower):
            found_countries.append(country_map[country_name])
    if len(set(found_countries)) == 1:
        country = found_countries[0]
    elif found_countries:
        issues.append('Multiple countries found; confirm the supplier-country restriction.')
    elif re.search(r'\b(?:from|country)\s+\w+', text_lower):
        issues.append('Country could not be resolved; explicitly select a country or Any.')
    max_price = None
    total_budget = None
    money = rf'(?:[₹$€£]|inr\s*|usd\s*|eur\s*|gbp\s*)?\s*({NUMBER})'
    amounts = list(re.finditer(rf'\b(?:under|below|maximum\s*(?:unit\s*)?(?:price)?|max\s*(?:unit\s*)?(?:price)?|budget\s*(?:of|is|:)?)\s*{money}', text_lower))
    budget_kind = 'unspecified'
    price_unit = None
    if len(amounts) > 1:
        issues.append('Multiple price/budget amounts found; enter one budget explicitly.')
    elif amounts:
        match = amounts[0]
        suffix = text_lower[match.end():]
        explicit_total = bool(re.search(r'\btotal\s+budget\b|\bbudget\s+total\b|\bin\s+total\b', text_lower))
        per_unit = re.match(rf'\s*(?:per\s+({UNIT})\b|(each)\b)', suffix)
        price_unit = canonical_unit(next((g for g in per_unit.groups() if g), None)) if per_unit else None
        budget_kind = 'total' if explicit_total else 'unit' if per_unit or 'unit price' in text_lower else 'unspecified'
        try:
            amount = parse_number(match.group(1))
            if explicit_total:
                total_budget = amount
            else:
                max_price = amount
        except ValueError:
            issues.append('Budget has invalid numeric formatting; enter it again.')
        if budget_kind == 'unspecified':
            issues.append('Confirm whether the budget is per catalog unit or for the whole line.')
    currency_symbols = {'₹': 'INR', '€': 'EUR', '£': 'GBP', '$': 'DOLLAR_UNSPECIFIED'}
    currencies = {code for symbol, code in currency_symbols.items() if symbol in requirement}
    currencies.update(code for code in ('INR', 'USD', 'EUR', 'GBP') if re.search(r'\b' + code + r'\b', requirement, re.I))
    if 'USD' in currencies:
        currencies.discard('DOLLAR_UNSPECIFIED')
    currency = next(iter(currencies)) if len(currencies) == 1 else None
    if len(currencies) > 1:
        issues.append('Multiple currencies found; conversion is not supported.')
    delivery_days = None
    match = re.search(rf'\b(?:within|delivery\s*(?:within|in)?|delivered\s*(?:within|in)?)\s*({NUMBER})\s*(days?|weeks?)\b', text_lower)
    if match:
        try:
            days = parse_number(match.group(1)) * (7 if match.group(2).startswith('week') else 1)
            if not days.is_integer():
                raise ValueError
            delivery_days = int(days)
        except ValueError:
            issues.append('Delivery must resolve to a positive whole number of days.')
    delivery_weight = 25
    quality_weight = 25
    experience_weight = 25
    price_weight = 25
    if 'delivery is most important' in text_lower or 'delivery is highest priority' in text_lower:
        delivery_weight = 50
        quality_weight = 25
        experience_weight = 10
        price_weight = 15
    elif 'quality is most important' in text_lower or 'quality is highest priority' in text_lower:
        delivery_weight = 20
        quality_weight = 50
        experience_weight = 15
        price_weight = 15
    elif 'price is most important' in text_lower or 'price is highest priority' in text_lower or 'lowest price' in text_lower:
        delivery_weight = 20
        quality_weight = 20
        experience_weight = 10
        price_weight = 50
    elif 'experience is most important' in text_lower or 'experience is highest priority' in text_lower:
        delivery_weight = 20
        quality_weight = 20
        experience_weight = 50
        price_weight = 10
    delivery_weight /= 100
    quality_weight /= 100
    experience_weight /= 100
    price_weight /= 100
    return dict(quantity=quantity, country=country, max_price=max_price, total_budget=total_budget,
                quantity_unit=quantity_unit, price_unit=price_unit, budget_kind=budget_kind,
                currency=currency, input_issues=issues, original_text=requirement,
                delivery_days=delivery_days, delivery_weight=delivery_weight, quality_weight=quality_weight,
                experience_weight=experience_weight, price_weight=price_weight)

def catalog_unit(product):
    """Return a label and a known base-unit multiplier, without inventing packs."""
    text = product.lower()
    if '(per ton)' in text:
        return 'metric ton (1,000 kg)', 'kg', 1000.0
    mass = re.search(r'\(per\s*(\d+)kg\)', text)
    if mass:
        size = float(mass.group(1))
        return f'{size:g} kg catalog unit', 'kg', size
    pack = re.search(r'\(per\s*(\d+)\)', text)
    if pack:
        size = float(pack.group(1))
        return f'pack of {size:g} individual items', 'each', size
    label = re.search(r'\(([^)]+)\)', product)
    if label:
        return label.group(1), None, None
    return f'one catalog unit of {product} (confirm scope)', None, None


def normalize_catalog_inputs(request):
    """Convert only compatible explicit units; unresolved values need buyer entry."""
    result = deepcopy(request)
    label, base, size = catalog_unit(result['product'])
    result['catalog_unit'] = label
    notes = []
    for value_key, unit_key, price in [('quantity', 'quantity_unit', False), ('max_price', 'price_unit', True)]:
        value, unit = result[value_key], result.get(unit_key)
        if value is None:
            continue
        if unit == 'catalog':
            continue
        if unit is None:
            if base is not None:
                result[value_key] = None
                notes.append(f'{value_key}: original {value:g} has no explicit unit; re-enter in {label}.')
            continue
        source_base, source_size = ('kg', 1000.0) if unit == 'ton' else ('kg', 1.0) if unit == 'kg' else (unit, 1.0)
        if base is not None and source_base == base:
            factor = size / source_size if price else source_size / size
            result[value_key] = value * factor
            result[unit_key] = 'catalog'
            if factor != 1:
                notes.append(f'{value_key}: converted {value:g} {unit} to {result[value_key]:g} per catalog basis.')
        elif unit == 'pack' and base == 'each':
            result[value_key] = None
            notes.append(f'{value_key}: pack size is unconfirmed; re-enter in packs of {size:g} items.')
        elif base is None and (unit == 'each' or unit in label.lower()):
            notes.append(f'{value_key}: confirm {value:g} uses the displayed catalog scope.')
        else:
            result[value_key] = None
            notes.append(f'{value_key}: cannot convert {unit} to {label}; enter a confirmed catalog value.')
    result['conversion_notes'] = notes
    return result


def confirm_number(label, value, whole=False):
    while True:
        default = f' [{value:g}]' if value is not None else ''
        answer = input(f'{label}{default}: ').strip()
        if not answer and value is not None:
            return value
        try:
            number = parse_number(answer)
            if whole and not number.is_integer():
                raise ValueError
            return int(number) if whole else number
        except ValueError:
            print('Enter a positive whole number.' if whole else 'Enter a positive number with valid comma grouping.')


def confirm_requirement(request, products):
    """Explicitly confirm comparable units and demo-money before any inference."""
    draft = deepcopy(request)
    print('\nCONFIRM THE REQUIREMENT — press Enter to keep a displayed numeric value.')
    print('Similarity does not verify specifications. Check the exact catalog product and scope.')
    while not draft.get('product_selected', False):
        answer = input(f"Use proposed product '{draft['product']}'? (yes/list/cancel): ").strip().lower()
        if answer == 'cancel':
            return None
        if answer == 'yes':
            break
        if answer == 'list':
            draft['product'] = read_category('Catalog product', products)
        else:
            print('Enter yes, list, or cancel.')
    draft = normalize_catalog_inputs(draft)
    for issue in draft.get('input_issues', []) + draft['conversion_notes']:
        print('Review:', issue)
    print('Currency in the synthetic historical data is unspecified.')
    if draft.get('currency'):
        print('Currency mentioned in your text:', draft['currency'])
    print('This run compares demonstration monetary units; no exchange-rate conversion or real-currency claim is made.')
    while True:
        answer = input("Type 'demo' to use demonstration amounts, or 'cancel': ").strip().lower()
        if answer == 'cancel':
            return None
        if answer == 'demo':
            draft['currency'] = 'DEMO'
            break
    while True:
        print('Catalog unit:', draft['catalog_unit'])
        draft['quantity'] = confirm_number('Quantity in catalog units', draft['quantity'])
        draft['delivery_days'] = confirm_number('Required delivery days', draft['delivery_days'], whole=True)
        while True:
            suggested = draft.get('country')
            answer = input(f"Supplier country [{suggested or 'unconfirmed'}] (name, 'any', or Enter to keep a country): ").strip()
            if answer:
                draft['country'] = None if answer.casefold() == 'any' else answer
                break
            if suggested:
                break
            print("Enter a supplier country or explicitly type 'any'.")
        print('Parsed budget:', draft.get('total_budget') if draft.get('total_budget') is not None else draft['max_price'],
              '| parsed type:', draft.get('budget_kind', 'unspecified'))
        kind = read_category('Budget basis', ['Unit price', 'Total line budget', 'No budget'])
        if kind == 'Unit price':
            draft['max_price'] = confirm_number('Maximum price per catalog unit (DEMO)', draft['max_price'])
            draft['total_budget'] = None
        elif kind == 'Total line budget':
            draft['total_budget'] = confirm_number('Total line budget excluding extra freight/tax (DEMO)', draft.get('total_budget'))
            draft['max_price'] = None
        else:
            draft['max_price'] = draft['total_budget'] = None
        draft['budget_kind'] = {'Unit price': 'unit', 'Total line budget': 'total', 'No budget': 'none'}[kind]
        validate_request(draft)
        print('\nCONFIRMED VALUES TO REVIEW')
        for label, key in [('Product', 'product'), ('Catalog unit', 'catalog_unit'), ('Quantity', 'quantity'),
                           ('Supplier country', 'country'), ('Unit-price limit', 'max_price'),
                           ('Total line budget', 'total_budget'), ('Delivery days', 'delivery_days')]:
            print(f'{label}: {draft[key]}')
        print('Currency: DEMO | Effective unit-price ceiling:', unit_budget(draft))
        print('Priorities:', ', '.join(f"{k.removesuffix('_weight')}: {draft[k]:.0%}" for k in WEIGHT_NAMES))
        while True:
            answer = input('Use these values? (yes/edit/cancel): ').strip().lower()
            if answer == 'yes':
                draft['confirmed'] = True
                draft['quantity_unit'] = draft['price_unit'] = 'catalog'
                return draft
            if answer == 'cancel':
                return None
            if answer == 'edit':
                break
            print('Enter yes, edit, or cancel.')


def predict_delivery_risk(supplier, request, supplier_history, risk_model, today, unit_price=None):
    if isinstance(risk_model, SupplierHistoryRisk):
        return risk_model.supplier_risk(supplier['supplier_id'], today)
    quantity = request['quantity']
    delivery_days = request['delivery_days']
    history = supplier_history[supplier_history['supplier_id'] == supplier['supplier_id']]
    if history.empty:
        previous_orders = 0
        supplier_late_rate = 0.0
        supplier_avg_delay = 0.0
    else:
        history = history.iloc[0]
        previous_orders = int(history['supplier_previous_orders'])
        supplier_late_rate = float(history['supplier_late_rate'])
        supplier_avg_delay = float(history['supplier_avg_delay'])
    unit_price = float(supplier['avg_unit_price'] if unit_price is None else unit_price)
    line_total = unit_price * quantity
    if not math.isfinite(line_total):
        raise ValueError('Order value is too large for model inference.')
    business_unit = request['business_unit']
    payment_terms = request['payment_terms']
    on_contract = request['on_contract']
    prediction_data = pd.DataFrame([{'supplier_id': supplier['supplier_id'], 'supplier_country': supplier['supplier_country'], 'category': supplier['category'], 'item': supplier['item'], 'business_unit': business_unit, 'payment_terms': payment_terms, 'unit_price': unit_price, 'quantity': quantity, 'line_total': line_total, 'on_contract': on_contract, 'promised_lead_days': delivery_days, 'supplier_previous_orders': previous_orders, 'supplier_late_rate': supplier_late_rate, 'supplier_avg_delay': supplier_avg_delay, 'order_month': today.month, 'order_dayofweek': today.weekday()}])
    risk_score = risk_model.predict_proba(prediction_data)[0][list(risk_model.classes_).index(1)]
    return risk_score * 100

def historical_risk(rate):
    if rate < 15:
        return 'LOW'
    elif rate < 30:
        return 'MEDIUM'
    else:
        return 'HIGH'

def recommend_suppliers(supplier_items, supplier_history, risk_model, request, today):
    validate_request(request)
    validate_commercial_inputs(request, risk_model)
    product = request['product']
    country = request['country']
    max_price = unit_budget(request)
    delivery_weight, quality_weight, experience_weight, price_weight = (request[k] for k in WEIGHT_NAMES)
    matches = supplier_items[supplier_items['item'] == product].copy()
    if country:
        matches = matches[matches['supplier_country'].str.lower() == country.lower()]
    if max_price is not None:
        matches = matches[matches['avg_unit_price'] <= max_price]
    if matches.empty:
        for column in ('match_score', 'ai_late_risk', 'rank', 'historical_risk'):
            matches[column] = pd.Series(index=matches.index, dtype='object')
        return matches
    matches['delivery_score'] = matches['on_time_rate']
    matches['quality_score'] = 100 - matches['rejection_rate']
    reference = scoring_reference(supplier_items, request)
    max_orders = reference['max_orders']
    if max_orders > 0:
        matches['experience_score'] = (matches['historical_orders'] / max_orders * 100).clip(0, 100)
    else:
        matches['experience_score'] = 0
    if max_price is not None:
        matches['price_score'] = (max_price - matches['avg_unit_price']) / max_price * 100
        matches['price_score'] = matches['price_score'].clip(lower=0, upper=100)
    else:
        cheapest = reference['min_price']
        matches['price_score'] = cheapest / matches['avg_unit_price'] * 100
    matches['match_score'] = matches['delivery_score'] * delivery_weight + matches['quality_score'] * quality_weight + matches['experience_score'] * experience_weight + matches['price_score'] * price_weight
    matches['historical_risk'] = matches['late_delivery_rate'].apply(historical_risk)
    matches['ai_late_risk'] = matches.apply(lambda supplier: predict_delivery_risk(supplier, request, supplier_history, risk_model, today), axis=1)
    if isinstance(risk_model, SupplierHistoryRisk):
        evidence = pd.DataFrame([risk_model.evidence(sid, today) for sid in matches.supplier_id], index=matches.index)
        matches = pd.concat([matches, evidence], axis=1)
    matches = matches.sort_values(['match_score', 'supplier_id'], ascending=[False, True], kind='mergesort')
    matches['rank'] = range(1, len(matches) + 1)
    return matches

def explain_supplier(supplier, request):
    quantity = request['quantity']
    max_price = unit_budget(request)
    delivery_weight, quality_weight, experience_weight, price_weight = (request[k] for k in WEIGHT_NAMES)
    reasons = []
    considerations = []
    if supplier['on_time_rate'] >= 95:
        reasons.append('Excellent historical on-time delivery performance')
    elif supplier['on_time_rate'] >= 85:
        reasons.append('Strong historical on-time delivery performance')
    else:
        considerations.append('Historical on-time delivery performance is relatively lower')
    if supplier['rejection_rate'] <= 2:
        reasons.append('Very low historical quality rejection rate')
    elif supplier['rejection_rate'] <= 5:
        reasons.append('Acceptable historical quality performance')
    else:
        considerations.append('Higher historical quality rejection rate')
    if supplier['historical_orders'] >= 50:
        reasons.append(f"Strong product experience with {int(supplier['historical_orders'])} historical orders")
    elif supplier['historical_orders'] >= 20:
        reasons.append(f"Has handled this product in {int(supplier['historical_orders'])} historical orders")
    else:
        considerations.append('Limited historical experience for this product')
    if quantity <= supplier['max_historical_quantity']:
        reasons.append('Requested quantity is within previously observed order size')
    else:
        considerations.append('Requested quantity is above the largest historically observed order')
    baseline = 'risk_method' in supplier
    if baseline and 0 < supplier.get('risk_completed_orders', 0) < 20:
        considerations.append('Risk evidence is limited: fewer than 20 known completed supplier orders')
    if baseline and supplier.get('risk_prior_only', False):
        considerations.append('No completed supplier history: risk shows only the overall prior, not supplier evidence')
    elif supplier['ai_late_risk'] < 15:
        reasons.append('Smoothed supplier-history late rate is relatively low' if baseline else 'AI model indicates relatively low late-delivery risk')
    elif supplier['ai_late_risk'] < 30:
        considerations.append('Smoothed supplier-history late rate is moderate (heuristic band)' if baseline else 'AI model indicates moderate late-delivery risk')
    else:
        considerations.append('Smoothed supplier-history late rate is elevated (heuristic band)' if baseline else 'AI model indicates elevated late-delivery risk')
    if max_price is not None:
        price_difference = max_price - supplier['avg_unit_price']
        if price_difference >= 0:
            reasons.append("Historical average unit price is within the buyer's budget")
    priority_values = {'Delivery': delivery_weight, 'Quality': quality_weight, 'Experience': experience_weight, 'Price': price_weight}
    highest = max(priority_values.values())
    priorities = [name.lower() for name, value in priority_values.items() if value == highest]
    reasons.append('Scoring reflects equally weighted buyer priorities' if len(priorities) == 4
                   else f"Scoring reflects the buyer's emphasis on {', '.join(priorities)}")
    return (reasons, considerations)

def display_recommendations(matches, request):
    quantity = request['quantity']
    print('\n====================================')
    print('AI PROCUREMENT RECOMMENDATIONS')
    print('====================================')
    print('\nHistorically compatible suppliers (not verified current offers):', len(matches))
    top_matches = matches.head(5)
    for rank, (_, supplier) in enumerate(top_matches.iterrows(), start=1):
        print('\n------------------------------------')
        print(f"#{rank} {supplier['supplier_name']}")
        print('Supplier ID:', supplier['supplier_id'])
        print('Country:', supplier['supplier_country'])
        print('Match Score:', round(supplier['match_score'], 2), '%')
        print('Supplier-history risk estimate:' if 'risk_method' in supplier else 'Experimental AI Late-Delivery Risk Score:', round(supplier['ai_late_risk'], 2), '%')
        if 'risk_method' in supplier:
            print('Risk evidence:', supplier['risk_evidence'])
            print(f"Known completed orders: {supplier['risk_completed_orders']} | Late: {supplier['risk_late_orders']} | Open: {supplier['risk_open_orders']} | Overdue: {supplier['risk_overdue_orders']}")
            print('Risk history cutoff: before', supplier['risk_as_of'], '(supplier-wide, all products)')
        print('Historical Risk:', supplier['historical_risk'])
        print('Item On-Time Rate:', supplier['on_time_rate'], '%')
        print('Quality Rejection Rate:', supplier['rejection_rate'], '%')
        print('Average Unit Price:', supplier['avg_unit_price'])
        print('Product Experience:', supplier['historical_orders'], 'historical orders')
        print('Largest Observed Order:', supplier['max_historical_quantity'])
        if quantity <= supplier['max_historical_quantity']:
            print('Quantity Check:', 'Previously handled')
        else:
            print('Quantity Check:', 'Above largest observed order')
        reasons, considerations = explain_supplier(supplier, request)
        print('\nWhy Recommended:')
        for reason in reasons:
            print('  +', reason)
        if considerations:
            print('\nConsiderations:')
            for consideration in considerations:
                print('  -', consideration)
    print('\n====================================')
    print('Synthetic demonstration data. Historical prices are not current quotations.')
    if request.get('risk_method') == 'supplier_history':
        print('Risk = (known late orders + 10 x fixed training prior) / (known completed orders + 10).')
        print('Only outcomes available before the decision day are used; delivery date proxies availability.')
        print('History-based estimates do not predict how changing this order will affect delivery.')
        print('Synthetic-only evaluation; reliability for new suppliers and real orders is unvalidated.')
    else:
        print('AI risk is experimental: training-history timing and calibration need validation.')
        print('Scenario risk changes are model sensitivity, not proven effects on real delivery.')
    print('Match score is a weighted index, not a suitability probability. Risk bands are heuristic.')
    print('Semantic Match Score represents embedding similarity, not probability.')
    print('Recommendation explanations are based on historical supplier metrics and buyer priorities.')
    print('Largest observed order is historical evidence, not supplier capacity.')


def compare_quotations(quotes, request, supplier_items, supplier_history, risk_model, today):
    """Evaluate full-order offers; never modify history, the request, or the model.

    All prices must use the same currency and unit as the buyer's budget.
    Quoted delivery is a promise, not independently verified capability.
    """
    validate_request(request)
    validate_commercial_inputs(request, risk_model)
    rows, seen = [], set()
    ceiling = unit_budget(request)
    for quote in quotes:
        supplier_id = quote['supplier_id']
        if supplier_id in seen:
            raise ValueError(f"Duplicate quote for {supplier_id}; enter one current offer per supplier.")
        seen.add(supplier_id)
        candidates = supplier_items[(supplier_items['supplier_id'] == supplier_id)
                                    & (supplier_items['item'] == request['product'])]
        if len(candidates) != 1:
            raise ValueError(f"Expected one supplier-product record for {supplier_id}.")
        supplier = candidates.iloc[0]
        if request.get('currency') and quote.get('currency', request['currency']) != request['currency']:
            raise ValueError('Quote and request currencies differ; currency conversion is not supported.')
        if request.get('catalog_unit') and quote.get('catalog_unit', request['catalog_unit']) != request['catalog_unit']:
            raise ValueError('Quote must use the confirmed catalog unit.')
        price = quote['unit_price']
        if not math.isfinite(price) or price <= 0:
            raise ValueError("Quoted unit price must be finite and positive.")
        order = deepcopy(request)
        order.update(quantity=quote['quantity'], delivery_days=quote['delivery_days'],
                     payment_terms=quote['payment_terms'], on_contract=quote['on_contract'])
        validate_request(order)
        validate_commercial_inputs(order, risk_model)
        if not math.isfinite(price * order['quantity']):
            raise ValueError("Quoted order value is too large.")
        reasons = []
        if request['country'] and str(supplier['supplier_country']).lower() != request['country'].lower():
            reasons.append("country differs from requirement")
        if request['max_price'] is not None and price > request['max_price']:
            reasons.append("unit price exceeds budget")
        if request.get('total_budget') is not None and price * order['quantity'] > request['total_budget']:
            reasons.append('line total exceeds total budget')
        if order['delivery_days'] > request['delivery_days']:
            reasons.append("promised delivery exceeds deadline")
        if order['quantity'] != request['quantity']:
            reasons.append("quantity differs from full requested order")
        row = supplier.to_dict()
        row.update(quoted_unit_price=price, quoted_quantity=order['quantity'],
                   quoted_days=order['delivery_days'], quoted_payment_terms=order['payment_terms'],
                   quoted_on_contract=order['on_contract'], quoted_total=price * order['quantity'],
                   eligible=not reasons, status='Eligible' if not reasons else '; '.join(reasons),
                   quote_score=float('nan'), quote_rank=float('nan'),
                   quote_ai_risk=predict_delivery_risk(supplier, order, supplier_history,
                                                      risk_model, today, unit_price=price))
        rows.append(row)
        if isinstance(risk_model, SupplierHistoryRisk):
            row.update(risk_model.evidence(supplier_id, today))
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    eligible = result['eligible']
    if eligible.any():
        offers = result.loc[eligible]
        reference = scoring_reference(supplier_items, request)
        maximum_orders = reference['max_orders']
        experience = (offers['historical_orders'] / maximum_orders * 100).clip(0, 100) if maximum_orders > 0 else 0
        if ceiling is None:
            price_score = (reference['min_price'] / offers['quoted_unit_price'] * 100).clip(0, 100)
        else:
            price_score = ((ceiling - offers['quoted_unit_price']) / ceiling * 100).clip(0, 100)
        result.loc[eligible, 'quote_score'] = (
            offers['on_time_rate'] * request['delivery_weight']
            + (100 - offers['rejection_rate']) * request['quality_weight']
            + experience * request['experience_weight']
            + price_score * request['price_weight'])
        ranked = result.loc[eligible].sort_values(['quote_score', 'supplier_id'], ascending=[False, True])
        result.loc[ranked.index, 'quote_rank'] = range(1, len(ranked) + 1)
    return result.sort_values(['quote_rank', 'supplier_id'], na_position='last').reset_index(drop=True)


def display_quotations(result, request):
    print("\nSUPPLIER QUOTATION COMPARISON — original buyer requirement")
    if result.empty:
        print("No quotations entered.")
        return
    columns = {
        'quote_rank': 'Rank', 'supplier_name': 'Supplier', 'supplier_id': 'Supplier ID',
        'avg_unit_price': 'Historical price', 'quoted_unit_price': 'Quote price',
        'quoted_quantity': 'Quantity', 'quoted_total': 'Line total', 'quoted_days': 'Days',
        'quoted_payment_terms': 'Payment terms', 'quoted_on_contract': 'Contract (1=yes)',
        'quote_score': 'Quote score %', 'quote_ai_risk': 'Risk %', 'status': 'Status',
    }
    if 'risk_method' in result.columns:
        columns.update(risk_completed_orders='Completed history', risk_late_orders='Known late', risk_evidence='Risk evidence')
    print(result[list(columns)].rename(columns=columns).to_string(
        index=False, na_rep='N/A', float_format=lambda n: f'{n:.2f}'))
    print("Line total = quoted unit price x quantity; extra freight/taxes are not included.")
    print('Historical metrics are synthetic. Risk is not a validated real-world probability.')
    print("Ranks use buyer weights, historical delivery/quality/experience, and quoted price.")
    print("Quoted days determine deadline eligibility, not the historical delivery score.")
    print("Risk is evaluated for every offer; ineligible offers receive no score or rank.")
    if 'risk_method' in result.columns:
        print('Supplier-history risk stays fixed across offers at the same decision date.')
        print('Quote price, quantity, terms and contract status cannot change historical outcomes.')
    else:
        print("Payment terms and contract status feed ML risk; they are not hard filters.")
    for _, row in result.iterrows():
        print(f"\n{row['supplier_name']}: {row['status']}")
        if row['quoted_quantity'] > row['max_historical_quantity']:
            print("  Quantity exceeds largest observed order; history does not establish capacity.")
        if row['quoted_payment_terms'] != request['payment_terms']:
            print(f"  Payment terms differ: {request['payment_terms']} -> {row['quoted_payment_terms']}")
        if row['quoted_on_contract'] != request['on_contract']:
            print("  Contract status differs from the original request.")
    if not result['eligible'].any():
        print("\nNo quotations satisfy all budget, country, deadline, and full-order quantity requirements.")


def quotation_session(request, supplier_items, supplier_history, risk_model, today):
    candidates = supplier_items[supplier_items['item'] == request['product']]
    print(f"\nEnter offers for {request['quantity']:g} units of {request['product']}.")
    print('Currency:', request.get('currency', 'unspecified'), '| Catalog unit:', request.get('catalog_unit', request['product']))
    print("Use the confirmed currency and catalog unit. No currency or quote-unit conversion is performed.")
    print(candidates[['supplier_id', 'supplier_name', 'supplier_country']].to_string(index=False))
    quotes = []
    terms = commercial_options(risk_model)['payment_terms']
    while True:
        answer = input("\nSupplier ID (or 'done' to compare, 'cancel' to return): ").strip()
        if answer.lower() == 'cancel':
            return
        if answer.lower() == 'done':
            break
        selected = candidates[candidates['supplier_id'].astype(str).str.casefold() == answer.casefold()]
        if len(selected) != 1:
            print("Select a supplier ID from the list.")
            continue
        supplier_id = selected.iloc[0]['supplier_id']
        if any(q['supplier_id'] == supplier_id for q in quotes):
            print("An offer for this supplier is already entered. Cancel and re-enter to revise offers.")
            continue
        quote = dict(supplier_id=supplier_id,
                     currency=request.get('currency'), catalog_unit=request.get('catalog_unit'),
                     unit_price=read_number("Quoted unit price: "),
                     quantity=read_number("Quantity covered by this quote: "),
                     delivery_days=read_number("Supplier's promised delivery days: ", whole=True),
                     payment_terms=read_category("Quoted payment terms", terms))
        while True:
            contract = input("Is this quote on contract? (yes/no): ").strip().lower()
            if contract in ('yes', 'y', 'no', 'n'):
                quote['on_contract'] = int(contract in ('yes', 'y'))
                break
            print("Please enter yes or no.")
        if not math.isfinite(quote['unit_price'] * quote['quantity']):
            print("Order value is too large. Please re-enter this quote.")
            continue
        quotes.append(quote)
        print("Quotation added.")
    result = compare_quotations(quotes, request, supplier_items, supplier_history, risk_model, today)
    display_quotations(result, request)


def main():
    from sentence_transformers import SentenceTransformer

    print("\nAI PROCUREMENT INTELLIGENCE SYSTEM")
    print('SYNTHETIC DEMONSTRATION — supplier names, prices and performance are generated data.')
    roots = (Path.cwd(), Path(__file__).resolve().parent,
             Path(__file__).resolve().parent.parent)
    root = next((p for p in roots if (p / "dataset/supplier_items.csv").exists()), roots[0])
    supplier_items = pd.read_csv(root / "dataset/supplier_items.csv")
    today = datetime.now()
    risk_model = SupplierHistoryRisk(pd.read_csv(root / 'dataset/procurement.csv'), today)
    supplier_history = risk_model.history
    print('Risk method: supplier-history baseline selected in Phase B (synthetic evaluation).')
    print(f'Fixed training prior: {risk_model.prior:.2%}; smoothing weight: 10 completed orders.')
    print('History cutoff: before', risk_model.as_of.date())
    print('Latest source order:', risk_model.last_order_date, '| Latest known outcome:', risk_model.last_outcome_date)
    if supplier_items.duplicated(["supplier_id", "item"]).any():
        raise ValueError("Supplier-item data must contain one row per supplier ID and item.")
    print("Supplier-item records:", len(supplier_items))
    print("Supplier history records:", len(supplier_history))
    products = sorted(supplier_items["item"].dropna().unique().tolist())
    if not products:
        print("No products are available.")
        return
    print("Loading semantic product model...")
    semantic_model = SentenceTransformer("all-MiniLM-L6-v2")
    search = ProductSearch(products, semantic_model)
    print('Search includes authored synonyms. Specifications still require confirmation.')
    print('Enter one product or service per request.')
    while True:
        requirement = input("\nDescribe your procurement requirement (or type 'cancel'):\n> ").strip()
        if requirement.casefold() == 'cancel':
            print('Procurement session cancelled.')
            return
        if not requirement:
            print("Nothing was entered. Paste or type your requirement at the > prompt below, then press Enter.")
            continue
        selected = select_product(search.search(requirement))
        if selected is not None:
            break
        print('Please revise the product description, or type cancel to exit.')
    similarity = selected['semantic_similarity']
    request = extract_requirements(requirement, supplier_items['supplier_country'].dropna().unique())
    request.update(product=selected['item'], semantic_match_score=similarity * 100,
                   search_score=selected['search_score'], product_selected=True)
    print("\nUNDERSTOOD REQUIREMENT")
    print("Product:", request["product"])
    print(f"Semantic retrieval similarity: {similarity * 100:.2f}% (similarity, not probability)")
    for label, field in (("Quantity", "quantity"), ("Country", "country"),
                         ("Maximum Unit Price", "max_price"), ("Delivery Days", "delivery_days")):
        print(f"{label}: {request[field]}")
    print("Buyer Priorities:")
    for field in WEIGHT_NAMES:
        print(f"  {field.removesuffix('_weight').title()}: {request[field] * 100:g}%")
    if similarity < 0.40:
        print("Low semantic similarity. Confirm an exact catalog match or cancel and revise the description.")
    request = confirm_requirement(request, products)
    if request is None:
        print('Requirement cancelled.')
        return
    request = collect_commercial_inputs(request, risk_model)
    # A fixed timestamp prevents unrelated calendar changes between scenarios.
    request['risk_method'] = 'supplier_history'
    request['decision_timestamp'] = today.isoformat(timespec='seconds')
    request['scoring_reference'] = scoring_reference(supplier_items, request)
    print('Decision timestamp:', request['decision_timestamp'])
    original_request = deepcopy(request)
    original_results = recommend_suppliers(
        supplier_items, supplier_history, risk_model, original_request, today
    ).copy(deep=True)
    display_recommendations(original_results, original_request)
    if original_results.empty:
        print("No suppliers meet the original product/country/budget constraints. You can still simulate a different budget.")
    what_if_loop(original_request, original_results, supplier_items,
                 supplier_history, risk_model, today)


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nProcurement session ended.")

