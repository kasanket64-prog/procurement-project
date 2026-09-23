import re


# ==========================================
# NATURAL LANGUAGE PROCUREMENT PARSER
# ==========================================

print("\nAI Procurement Requirement Parser")
print("=================================")

requirement = input(
    "\nDescribe your procurement requirement:\n> "
).strip()


# ==========================================
# DEFAULT VALUES
# ==========================================

product = None
quantity = None
country = None
max_price = None
delivery_days = None


# ==========================================
# 1. PRODUCT DETECTION
# ==========================================

product_keywords = {
    "steel coil": "Steel Coil (per ton)",
    "aluminium sheet": "Aluminium Sheet (per ton)",
    "aluminum sheet": "Aluminium Sheet (per ton)",
    "copper wire": "Copper Wire Rod (per ton)",
    "polypropylene": "Polypropylene Resin (per ton)",
    "rubber compound": "Rubber Compound (per ton)",
    "industrial bearings": "Industrial Bearings",
    "office chairs": "Office Chairs",
    "wooden pallets": "Wooden Pallets",
    "safety gloves": "Safety Gloves (per 100)",
    "sensor module": "Sensor Module SM-3",
    "microcontroller": "Microcontroller MCU-9",
    "pcb assembly": "PCB Assembly A-11"
}

text_lower = requirement.lower()

for keyword, item_name in product_keywords.items():

    if keyword in text_lower:

        product = item_name
        break


# ==========================================
# 2. QUANTITY DETECTION
# ==========================================

quantity_patterns = [
    r"(\d+(?:\.\d+)?)\s*tons?",
    r"(\d+(?:\.\d+)?)\s*tonnes?",
    r"quantity\s*(?:of|:)?\s*(\d+(?:\.\d+)?)",
    r"need\s*(\d+(?:\.\d+)?)"
]

for pattern in quantity_patterns:

    match = re.search(
        pattern,
        text_lower
    )

    if match:

        quantity = float(
            match.group(1)
        )

        break


# ==========================================
# 3. COUNTRY DETECTION
# ==========================================

countries = [
    "china",
    "india",
    "japan",
    "germany",
    "usa",
    "united states",
    "uk",
    "united kingdom",
    "france",
    "italy",
    "south korea",
    "singapore"
]

for country_name in countries:

    if country_name in text_lower:

        country = country_name.title()
        break


# ==========================================
# 4. MAXIMUM PRICE DETECTION
# ==========================================

price_patterns = [
    r"under\s*[₹$]?\s*(\d+(?:\.\d+)?)",
    r"below\s*[₹$]?\s*(\d+(?:\.\d+)?)",
    r"maximum\s*(?:price)?\s*[₹$]?\s*(\d+(?:\.\d+)?)",
    r"max\s*(?:price)?\s*[₹$]?\s*(\d+(?:\.\d+)?)",
    r"budget\s*(?:of|is|:)?\s*[₹$]?\s*(\d+(?:\.\d+)?)"
]

for pattern in price_patterns:

    match = re.search(
        pattern,
        text_lower
    )

    if match:

        max_price = float(
            match.group(1)
        )

        break


# ==========================================
# 5. DELIVERY DAYS DETECTION
# ==========================================

delivery_patterns = [
    r"within\s*(\d+)\s*days?",
    r"delivery\s*(?:within|in)?\s*(\d+)\s*days?",
    r"delivered\s*(?:within|in)?\s*(\d+)\s*days?"
]

for pattern in delivery_patterns:

    match = re.search(
        pattern,
        text_lower
    )

    if match:

        delivery_days = int(
            match.group(1)
        )

        break


# ==========================================
# 6. SIMPLE PRIORITY DETECTION
# ==========================================

delivery_weight = 25
quality_weight = 25
experience_weight = 25
price_weight = 25


if (
    "delivery is most important" in text_lower
    or "delivery is highest priority" in text_lower
):

    delivery_weight = 50
    quality_weight = 25
    experience_weight = 10
    price_weight = 15


elif (
    "quality is most important" in text_lower
    or "quality is highest priority" in text_lower
):

    delivery_weight = 20
    quality_weight = 50
    experience_weight = 15
    price_weight = 15


elif (
    "price is most important" in text_lower
    or "price is highest priority" in text_lower
    or "lowest price" in text_lower
):

    delivery_weight = 20
    quality_weight = 20
    experience_weight = 10
    price_weight = 50


elif (
    "experience is most important" in text_lower
    or "experience is highest priority" in text_lower
):

    delivery_weight = 20
    quality_weight = 20
    experience_weight = 50
    price_weight = 10


# ==========================================
# 7. DISPLAY STRUCTURED REQUIREMENT
# ==========================================

print("\n=================================")
print("EXTRACTED PROCUREMENT REQUIREMENT")
print("=================================")

print(
    "Product:",
    product if product else "Not detected"
)

print(
    "Quantity:",
    quantity if quantity is not None else "Not detected"
)

print(
    "Country:",
    country if country else "Any"
)

print(
    "Maximum Unit Price:",
    max_price if max_price is not None else "Not specified"
)

print(
    "Delivery Days:",
    delivery_days if delivery_days is not None else "Not detected"
)


print("\nBuyer Priorities")

print(
    "Delivery:",
    delivery_weight,
    "%"
)

print(
    "Quality:",
    quality_weight,
    "%"
)

print(
    "Experience:",
    experience_weight,
    "%"
)

print(
    "Price:",
    price_weight,
    "%"
)


# ==========================================
# 8. CREATE STRUCTURED DATA
# ==========================================

structured_requirement = {

    "product": product,

    "quantity": quantity,

    "country": country,

    "max_unit_price": max_price,

    "delivery_days": delivery_days,

    "priorities": {

        "delivery": delivery_weight,

        "quality": quality_weight,

        "experience": experience_weight,

        "price": price_weight
    }
}


print("\nStructured Requirement:")

print(
    structured_requirement
)