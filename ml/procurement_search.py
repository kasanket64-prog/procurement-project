"""Catalog retrieval with explicit confirmation, conservative known-spec guards."""
from pathlib import Path
import json
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


def model_tokens(text):
    tokens = re.findall(r'\b(?:(?:CK|MCU|SM)[ -]?\d+|A-\d+)\b', text, re.I)
    return {re.sub(r'^(CK|MCU|SM)[ -]?(\d+)$', r'\1-\2', token.upper()) for token in tokens}


class ProductSearch:
    def __init__(self, products, model, catalog_path=None):
        self.products = sorted(set(products))
        if not self.products:
            raise ValueError('Catalog is empty.')
        path = Path(catalog_path) if catalog_path else Path(__file__).with_name('search_catalog.json')
        data = json.loads(path.read_text(encoding='utf-8'))
        entries = data['items']
        names = [row['item'] for row in entries]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate enriched catalog items.')
        mapping = {row['item']: row for row in entries}
        self.missing_enrichment = [name for name in self.products if name not in mapping]
        self.documents = [name + '. ' + '. '.join(mapping.get(name, {}).get('aliases', [])) for name in self.products]
        self.model = model
        self.names = np.asarray(model.encode(self.products, normalize_embeddings=True))
        self.enriched = np.asarray(model.encode(self.documents, normalize_embeddings=True))
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), strip_accents='unicode')
        self.lexical = self.vectorizer.fit_transform(self.documents)

    def scores(self, queries):
        embeddings = np.asarray(self.model.encode(list(queries), normalize_embeddings=True))
        name = embeddings @ self.names.T
        enriched = embeddings @ self.enriched.T
        lexical = (self.vectorizer.transform(queries) @ self.lexical.T).toarray()
        semantic = .4 * name + .6 * enriched
        return {'name_only': name, 'enriched': enriched, 'lexical': lexical,
                'hybrid': .85 * semantic + .15 * lexical, 'semantic': semantic}

    def unsupported_known_spec(self, query):
        requested = model_tokens(query)
        known = set().union(*(model_tokens(name) for name in self.products))
        missing = requested - known
        if missing:
            return 'Requested model is not in this catalog: ' + ', '.join(sorted(missing))
        watts = re.search(r'\b(\d+)\s*(?:w|watts?)\b', query, re.I)
        if watts and re.search(r'power\s*suppl|\bpsu\b', query, re.I):
            supported = {int(w) for name in self.products for w in re.findall(r'\b(\d+)W\b', name, re.I)}
            if supported and int(watts.group(1)) not in supported:
                return 'The requested power-supply wattage is not in this catalog.'
        feet = re.search(r'\b(\d+)\s*(?:ft|foot|feet)\b', query, re.I)
        if feet and 'container' in query.lower():
            supported = {int(w) for name in self.products for w in re.findall(r'\b(\d+)ft\b', name, re.I)}
            if supported and int(feet.group(1)) not in supported:
                return 'The requested container size is not in this catalog.'
        return None

    def search(self, query, k=3):
        return self.result_from_scores(query, self.scores([query]), k)

    def result_from_scores(self, query, scores, k=3):
        if not query.strip():
            return {'candidates': [], 'reliable': False, 'reason': 'Enter a product description.'}
        conflict = self.unsupported_known_spec(query)
        if conflict:
            return {'candidates': [], 'reliable': False, 'reason': conflict}
        order = np.argsort(-scores['hybrid'][0], kind='stable')
        candidates = [{'item': self.products[i], 'search_score': float(scores['hybrid'][0, i]),
                       'semantic_similarity': float(scores['semantic'][0, i])} for i in order[:k]]
        margin = scores['hybrid'][0, order[0]] - scores['hybrid'][0, order[1]] if len(order) > 1 else 1
        reliable = candidates[0]['semantic_similarity'] >= .40 and margin >= .035
        return {'candidates': candidates, 'reliable': bool(reliable),
                'reason': 'Confirm the catalog item and specifications.' if reliable else 'No reliable automatic match: the description is weak or multiple products are similar.'}


def select_product(result):
    """Never turn the closest embedding into an automatically accepted product."""
    print('\nPRODUCT SEARCH')
    print(result['reason'])
    if not result['candidates']:
        return None
    for i, row in enumerate(result['candidates'], 1):
        print(f"{i}. {row['item']} | semantic similarity {row['semantic_similarity']:.1%}")
    print('Similarity is not a probability or proof of specification compliance.')
    while True:
        answer = input("Select a matching product number, or 'none' to revise the request: ").strip().lower()
        if answer in ('none', 'cancel'):
            return None
        if answer.isascii() and answer.isdecimal() and 1 <= int(answer) <= len(result['candidates']):
            return result['candidates'][int(answer)-1]
        print('Choose one of the displayed numbers or type none.')
