"""Synthetic test suppliers used only for backend tests.
These fixtures are NOT included in the production /api/suppliers response.
"""

def get_test_suppliers():
    return [
        {
            "id": "SUP-GRADE-100Cr6",
            "name": "GradeConfirmed Ltd",
            "country": "Germany",
            "evidence": [
                {"title": "Deep groove bearings grade 100Cr6", "description": "Certified 100Cr6 steel bearings"}
            ],
            "delivery": "10 days",
            "min_order": 50,
        },
        {
            "id": "SUP-NOGRADE",
            "name": "NoGrade Supplies",
            "country": "France",
            "evidence": [
                {"title": "Standard bearings", "description": "General bearings without grade spec"}
            ],
            "delivery": "12 days",
            "min_order": 20,
        },
        {
            "id": "SUP-MIN500",
            "name": "LargeOrder Co",
            "country": "USA",
            "evidence": [
                {"title": "Deep groove bearings grade 100Cr6", "description": "High volume supply"}
            ],
            "delivery": "15 days",
            "min_order": 500,
        },
    ]
