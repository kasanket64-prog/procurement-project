"""Procurement recommendations and independent What-If simulations.

Run from the existing AI-Supply-Chain project root, or put this file in ml/.
Loads the existing trained model; never trains or changes it.
Budget always means maximum unit price, matching the original program.
Delivery and quantity affect ML risk, not eligibility: the source data has
no verified delivery commitment or capacity. Historical order size is only
an observation. Ranking remains based on the weighted supplier match score.
"""
from datetime import datetime
from pathlib import Path
from copy import deepcopy
import math
import re
import pandas as pd
import joblib


def validate_request(request):
    for field in ("quantity", "delivery_days", "max_price"):
        value = request[field]
        if field == "max_price" and value is None:
            continue
        if value is None or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{field} must be a finite positive number.")
    if int(request["delivery_days"]) != request["delivery_days"]:
        raise ValueError("Delivery days must be a whole number.")


def commercial_options(risk_model):
    """Read known categories from the fitted encoder without fitting anything."""
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
            if answer.casefold() == option.casefold():
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
    elif field in ("max_price", "delivery_days", "quantity"):
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
            change = "REMOVED: exceeds what-if unit-price budget"
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
            "Original AI risk %": row["ai_late_risk_original"],
            "What-if AI risk %": row["ai_late_risk_what_if"],
            "Rank change": change,
        })
    return pd.DataFrame(rows)


def read_number(prompt, whole=False, allow_any=False):
    while True:
        text = input(prompt).strip()
        if allow_any and text.lower() == "any":
            return None
        try:
            value = float(text.replace(",", ""))
            if not math.isfinite(value) or value <= 0 or (whole and not value.is_integer()):
                raise ValueError
            return int(value) if whole else value
        except ValueError:
            print("Enter a positive whole number." if whole else "Enter a finite positive number.")


def what_if_loop(original_request, original_results, supplier_items,
                 supplier_history, risk_model, today):
    print("\nEach simulation changes one input from the ORIGINAL request.")
    print("Budget is maximum unit price. Quantity uses the product's existing units.")
    print("Delivery days and quantity affect AI risk; verified lead-time/capacity constraints are unavailable.")
    while True:
        print("\n1 Change Budget\n2 Change Delivery Days\n3 Change Quantity\n4 Change Buyer Priorities\n5 Exit")
        choice = input("Choose: ").strip()
        if choice == "5":
            return
        if choice == "1":
            field, value = "max_price", read_number("Maximum unit price (or 'any'): ", allow_any=True)
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
            print("Select an option from 1 to 5.")
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
        print("AI risk is reported separately; ranks use the weighted match score.")
        display_recommendations(results, request)

PRIORITY_PRESETS = {
    "Delivery": (0.50, 0.25, 0.10, 0.15),
    "Quality": (0.20, 0.50, 0.15, 0.15),
    "Price": (0.20, 0.20, 0.10, 0.50),
    "Experience": (0.20, 0.20, 0.50, 0.10),
}
WEIGHT_NAMES = ("delivery_weight", "quality_weight", "experience_weight", "price_weight")

def extract_requirements(requirement):
    text_lower = requirement.lower()
    quantity = None
    quantity_patterns = ['(\\d+(?:\\.\\d+)?)\\s*tons?', '(\\d+(?:\\.\\d+)?)\\s*tonnes?', 'quantity\\s*(?:of|:)?\\s*(\\d+(?:\\.\\d+)?)', 'need\\s*(\\d+(?:\\.\\d+)?)']
    for pattern in quantity_patterns:
        match = re.search(pattern, text_lower)
        if match:
            quantity = float(match.group(1))
            break
    country = None
    country_map = {'china': 'China', 'india': 'India', 'japan': 'Japan', 'germany': 'Germany', 'united states': 'USA', 'usa': 'USA', 'united kingdom': 'UK', 'uk': 'UK', 'france': 'France', 'italy': 'Italy', 'south korea': 'South Korea', 'singapore': 'Singapore'}
    for country_name in sorted(country_map, key=len, reverse=True):
        if re.search('\\b' + re.escape(country_name) + '\\b', text_lower):
            country = country_map[country_name]
            break
    max_price = None
    price_patterns = ['under\\s*[₹$]?\\s*(\\d+(?:\\.\\d+)?)', 'below\\s*[₹$]?\\s*(\\d+(?:\\.\\d+)?)', 'maximum\\s*(?:unit\\s*)?(?:price)?\\s*[₹$]?\\s*(\\d+(?:\\.\\d+)?)', 'max\\s*(?:unit\\s*)?(?:price)?\\s*[₹$]?\\s*(\\d+(?:\\.\\d+)?)', 'budget\\s*(?:of|is|:)?\\s*[₹$]?\\s*(\\d+(?:\\.\\d+)?)']
    for pattern in price_patterns:
        match = re.search(pattern, text_lower)
        if match:
            max_price = float(match.group(1))
            break
    delivery_days = None
    delivery_patterns = ['within\\s*(\\d+)\\s*days?', 'delivery\\s*(?:within|in)?\\s*(\\d+)\\s*days?', 'delivered\\s*(?:within|in)?\\s*(\\d+)\\s*days?']
    for pattern in delivery_patterns:
        match = re.search(pattern, text_lower)
        if match:
            delivery_days = int(match.group(1))
            break
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
    return dict(quantity=quantity, country=country, max_price=max_price, delivery_days=delivery_days, delivery_weight=delivery_weight, quality_weight=quality_weight, experience_weight=experience_weight, price_weight=price_weight)

def predict_delivery_risk(supplier, request, supplier_history, risk_model, today):
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
    unit_price = float(supplier['avg_unit_price'])
    line_total = unit_price * quantity
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
    max_price = request['max_price']
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
    max_orders = matches['historical_orders'].max()
    if max_orders > 0:
        matches['experience_score'] = matches['historical_orders'] / max_orders * 100
    else:
        matches['experience_score'] = 0
    if max_price is not None:
        matches['price_score'] = (max_price - matches['avg_unit_price']) / max_price * 100
        matches['price_score'] = matches['price_score'].clip(lower=0, upper=100)
    else:
        cheapest = matches['avg_unit_price'].min()
        matches['price_score'] = cheapest / matches['avg_unit_price'] * 100
    matches['match_score'] = matches['delivery_score'] * delivery_weight + matches['quality_score'] * quality_weight + matches['experience_score'] * experience_weight + matches['price_score'] * price_weight
    matches['historical_risk'] = matches['late_delivery_rate'].apply(historical_risk)
    matches['ai_late_risk'] = matches.apply(lambda supplier: predict_delivery_risk(supplier, request, supplier_history, risk_model, today), axis=1)
    matches = matches.sort_values('match_score', ascending=False, kind='mergesort')
    matches['rank'] = range(1, len(matches) + 1)
    return matches

def explain_supplier(supplier, request):
    quantity = request['quantity']
    max_price = request['max_price']
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
    if supplier['ai_late_risk'] < 15:
        reasons.append('AI model indicates relatively low late-delivery risk')
    elif supplier['ai_late_risk'] < 30:
        considerations.append('AI model indicates moderate late-delivery risk')
    else:
        considerations.append('AI model indicates elevated late-delivery risk')
    if max_price is not None:
        price_difference = max_price - supplier['avg_unit_price']
        if price_difference >= 0:
            reasons.append("Historical average unit price is within the buyer's budget")
    priority_values = {'Delivery': delivery_weight, 'Quality': quality_weight, 'Experience': experience_weight, 'Price': price_weight}
    highest_priority = max(priority_values, key=priority_values.get)
    reasons.append(f"Scoring reflects the buyer's emphasis on {highest_priority.lower()}")
    return (reasons, considerations)

def display_recommendations(matches, request):
    quantity = request['quantity']
    print('\n====================================')
    print('AI PROCUREMENT RECOMMENDATIONS')
    print('====================================')
    print('\nEligible suppliers:', len(matches))
    top_matches = matches.head(5)
    for rank, (_, supplier) in enumerate(top_matches.iterrows(), start=1):
        print('\n------------------------------------')
        print(f"#{rank} {supplier['supplier_name']}")
        print('Supplier ID:', supplier['supplier_id'])
        print('Country:', supplier['supplier_country'])
        print('Match Score:', round(supplier['match_score'], 2), '%')
        print('AI Late-Delivery Risk Score:', round(supplier['ai_late_risk'], 2), '%')
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
    print('Note: AI risk is a decision-support score based on historical data.')
    print('Semantic Match Score represents embedding similarity, not probability.')
    print('Recommendation explanations are based on historical supplier metrics and buyer priorities.')
    print('Largest observed order is historical evidence, not supplier capacity.')


def main():
    from sentence_transformers import SentenceTransformer, util

    print("\nAI PROCUREMENT INTELLIGENCE SYSTEM")
    roots = (Path.cwd(), Path(__file__).resolve().parent,
             Path(__file__).resolve().parent.parent)
    root = next((p for p in roots if (p / "dataset/supplier_items.csv").exists()), roots[0])
    supplier_items = pd.read_csv(root / "dataset/supplier_items.csv")
    supplier_history = pd.read_csv(root / "dataset/supplier_history.csv")
    risk_model = joblib.load(root / "models/delivery_risk_model_clean.pkl")
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
    embeddings = semantic_model.encode(products, convert_to_tensor=True, normalize_embeddings=True)
    requirement = input("\nDescribe your procurement requirement:\n> ").strip()
    if not requirement:
        print("Please enter a procurement requirement.")
        return
    query = semantic_model.encode(requirement, convert_to_tensor=True, normalize_embeddings=True)
    similarities = util.cos_sim(query, embeddings)[0]
    best_index = similarities.argmax().item()
    similarity = similarities[best_index].item()
    request = extract_requirements(requirement)
    request.update(product=products[best_index], semantic_match_score=similarity * 100)
    print("\nUNDERSTOOD REQUIREMENT")
    print("Product:", request["product"])
    print(f"Semantic Product Match: {similarity * 100:.2f}% (similarity, not probability)")
    for label, field in (("Quantity", "quantity"), ("Country", "country"),
                         ("Maximum Unit Price", "max_price"), ("Delivery Days", "delivery_days")):
        print(f"{label}: {request[field]}")
    print("Buyer Priorities:")
    for field in WEIGHT_NAMES:
        print(f"  {field.removesuffix('_weight').title()}: {request[field] * 100:g}%")
    if similarity < 0.40:
        print("Product could not be matched reliably. Please provide a clearer description.")
        return
    try:
        validate_request(request)
    except ValueError as exc:
        print(f"Invalid or missing requirement: {exc}")
        return
    request = collect_commercial_inputs(request, risk_model)
    # A fixed timestamp prevents unrelated calendar changes between scenarios.
    today = datetime.now()
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

