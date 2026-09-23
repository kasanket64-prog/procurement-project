from sentence_transformers import SentenceTransformer, util
import pandas as pd
from sentence_transformers import SentenceTransformer, util


# ==========================================
# 1. LOAD SUPPLIER PRODUCT DATA
# ==========================================

df = pd.read_csv(
    "dataset/supplier_items.csv"
)

products = sorted(
    df["item"]
    .dropna()
    .unique()
    .tolist()
)

print("\n==============================")
print("SEMANTIC PRODUCT MATCHER")
print("==============================")

print(
    "Products available:",
    len(products)
)


# ==========================================
# 2. LOAD SEMANTIC AI MODEL
# ==========================================

print("\nLoading semantic model...")

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

print("Semantic model loaded!")


# ==========================================
# 3. CREATE PRODUCT EMBEDDINGS
# ==========================================

product_embeddings = model.encode(
    products,
    convert_to_tensor=True,
    normalize_embeddings=True
)


# ==========================================
# 4. BUYER INPUT
# ==========================================

query = input(
    "\nWhat product are you looking for?\n> "
).strip()


# ==========================================
# 5. CONVERT BUYER TEXT TO EMBEDDING
# ==========================================

query_embedding = model.encode(
    query,
    convert_to_tensor=True,
    normalize_embeddings=True
)


# ==========================================
# 6. CALCULATE SEMANTIC SIMILARITY
# ==========================================

similarities = util.cos_sim(
    query_embedding,
    product_embeddings
)[0]


# ==========================================
# 7. GET TOP MATCHES
# ==========================================

top_results = similarities.topk(
    k=min(5, len(products))
)


print("\n==============================")
print("TOP SEMANTIC PRODUCT MATCHES")
print("==============================")


for rank, (score, index) in enumerate(
    zip(
        top_results.values,
        top_results.indices
    ),
    start=1
):

    product = products[
        index.item()
    ]

    similarity = (
        score.item() * 100
    )

    print(
        f"\n#{rank} {product}"
    )

    print(
        "Semantic Similarity:",
        round(similarity, 2),
        "%"
    )


# ==========================================
# 8. BEST MATCH
# ==========================================

best_index = (
    top_results.indices[0].item()
)

best_score = (
    top_results.values[0].item()
)

best_product = products[
    best_index
]


print("\n==============================")
print("BEST PRODUCT MATCH")
print("==============================")

print(
    "Buyer Input:",
    query
)

print(
    "Matched Product:",
    best_product
)

print(
    "Confidence Score:",
    round(
        best_score * 100,
        2
    ),
    "%"
)


# ==========================================
# 9. LOW-CONFIDENCE WARNING
# ==========================================

if best_score < 0.40:

    print(
        "\nWARNING: Product match confidence "
        "is low."
    )

    print(
        "Ask the buyer to confirm the product."
    )