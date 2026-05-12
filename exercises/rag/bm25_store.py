"""
BM25 Index — Lexical (Keyword) Search
======================================
Classic text search using the BM25 (Best Match 25) algorithm.

How BM25 works:
  1. Tokenize: break documents and queries into words
  2. Term Frequency (TF): how often a word appears in a document
  3. Inverse Document Frequency (IDF): rare words across all docs get higher weight
  4. Score: documents score higher when they contain rare, query-specific terms

Why BM25 complements semantic search:
  - Semantic search: great at understanding MEANING and CONTEXT
  - BM25: great at finding EXACT term matches (IDs, names, codes)

  Example: searching for "INC-2023-Q4-011"
    Semantic search might return vaguely related security sections
    BM25 will find the EXACT section containing that incident ID

Together (hybrid search) they cover both conceptual and exact matches.

This is a simplified BM25 implementation. Production systems use
libraries like rank_bm25 or Elasticsearch's built-in BM25.
"""

import math
import re
from collections import Counter


class BM25Index:
    """
    In-memory BM25 lexical search index.

    Parameters tuned for general use:
      - k1=1.5: controls term frequency saturation
      - b=0.75: controls document length normalization
    """

    def __init__(self, k1=1.5, b=0.75):
        self._documents = []
        self._tokenized_docs = []
        self._doc_lengths = []
        self._doc_freq = Counter()
        self._k1 = k1
        self._b = b

    def _tokenize(self, text):
        """
        Simple tokenization: lowercase + split on non-alphanumeric.
        Handles hyphenated terms like "INC-2023-Q4-011" as separate tokens.
        """
        text = text.lower()
        tokens = re.findall(r"[a-z0-9]+", text)
        return tokens

    def add_document(self, document):
        """
        Add a document to the BM25 index.

        Args:
            document: Dict with at least a "content" key.
        """
        tokens = self._tokenize(document["content"])
        self._documents.append(document)
        self._tokenized_docs.append(tokens)
        self._doc_lengths.append(len(tokens))

        # Track how many documents contain each unique term
        unique_terms = set(tokens)
        for term in unique_terms:
            self._doc_freq[term] += 1

    def search(self, query_text, k=3):
        """
        Find the k most relevant documents for a query using BM25 scoring.

        Args:
            query_text: The search query string.
            k: Number of results to return.

        Returns:
            List of (document, score) tuples, sorted by score (highest first).
            Score is BM25 relevance — higher = more relevant.
            We convert to distance-like format for consistency with VectorIndex.
        """
        if not self._documents:
            return []

        query_tokens = self._tokenize(query_text)
        avg_doc_length = sum(self._doc_lengths) / len(self._doc_lengths)
        total_docs = len(self._documents)

        scores = []
        for i, doc_tokens in enumerate(self._tokenized_docs):
            score = self._bm25_score(
                query_tokens, doc_tokens,
                self._doc_lengths[i], avg_doc_length, total_docs
            )
            scores.append((i, score))

        # Sort by score descending (highest = most relevant)
        scores.sort(key=lambda x: x[1], reverse=True)

        # Return top-k as (document, distance) tuples
        # Convert BM25 score to distance: 1 / (1 + score)
        # This makes it compatible with VectorIndex's "lower = better" semantics
        results = []
        for idx, score in scores[:k]:
            distance = 1.0 / (1.0 + max(score, 0))
            results.append((self._documents[idx], distance))

        return results

    def _bm25_score(self, query_tokens, doc_tokens, doc_length, avg_dl, total_docs):
        """
        Calculate BM25 score for a single document against a query.

        BM25 formula per query term:
          IDF(q) = log((N - n(q) + 0.5) / (n(q) + 0.5))
          TF(q,d) = f(q,d) * (k1 + 1) / (f(q,d) + k1 * (1 - b + b * |d| / avgdl))
          score += IDF(q) * TF(q,d)

        Where:
          N = total documents
          n(q) = documents containing term q
          f(q,d) = frequency of term q in document d
          |d| = document length
          avgdl = average document length
        """
        doc_term_freq = Counter(doc_tokens)
        score = 0.0

        for term in query_tokens:
            if term not in doc_term_freq:
                continue

            # IDF: how rare is this term?
            n_docs_with_term = self._doc_freq.get(term, 0)
            idf = math.log((total_docs - n_docs_with_term + 0.5) / (n_docs_with_term + 0.5))

            # TF with saturation and length normalization
            tf = doc_term_freq[term]
            tf_normalized = tf * (self._k1 + 1) / (
                tf + self._k1 * (1 - self._b + self._b * doc_length / avg_dl)
            )

            score += idf * tf_normalized

        return score

    def __len__(self):
        return len(self._documents)
