"""
Vector Store — Semantic Search with Cosine Similarity
======================================================
Stores text embeddings and finds the most similar ones using cosine similarity.

How it works:
  1. Add documents: each document's text gets embedded (via VoyageAI)
     and stored as a vector (list of floats)
  2. Search: embed the query, compare it to ALL stored vectors using
     cosine similarity, return the top-K closest matches

Cosine Similarity:
  Measures the cosine of the angle between two vectors.
    1.0 = identical direction (most similar)
    0.0 = perpendicular (unrelated)
   -1.0 = opposite direction (most different)

  Formula: cos(A,B) = (A . B) / (|A| * |B|)

Cosine Distance:
  1 - cosine_similarity. Lower = more similar. This is what we return
  so that "distance" semantics match intuition (closer = better).

This is a simple in-memory implementation. Production systems use
dedicated vector databases like Pinecone, Weaviate, ChromaDB, or
pgvector for scale and persistence.
"""

import math
from embeddings import generate_embedding


class VectorIndex:
    """
    In-memory vector store using cosine similarity for search.

    Each document is stored as:
      - embedding: list of floats (the vector)
      - metadata: dict with the original text and any extra fields
    """

    def __init__(self):
        self._documents = []
        self._embeddings = []

    def add_document(self, document, embedding=None):
        """
        Add a document to the vector store.

        Args:
            document: Dict with at least a "content" key containing text.
            embedding: Pre-computed embedding. If None, generates one from content.
        """
        if embedding is None:
            embedding = generate_embedding(document["content"])

        self._documents.append(document)
        self._embeddings.append(embedding)

    def search(self, query_text, k=3):
        """
        Find the k most similar documents to a query.

        Args:
            query_text: The search query string.
            k: Number of results to return.

        Returns:
            List of (document, distance) tuples, sorted by distance (closest first).
            Distance is cosine distance: 1 - cosine_similarity.
        """
        if not self._embeddings:
            return []

        # Embed the query using "query" input type for better search quality
        query_embedding = generate_embedding(query_text, input_type="query")
        return self.search_with_embedding(query_embedding, k=k)

    def search_with_embedding(self, query_embedding, k=3):
        """
        Find the k most similar documents using a pre-computed query embedding.
        Use this when you batch-compute embeddings to avoid rate limits.

        Args:
            query_embedding: Pre-computed embedding vector for the query.
            k: Number of results to return.

        Returns:
            List of (document, distance) tuples, sorted by distance (closest first).
        """
        if not self._embeddings:
            return []

        distances = []
        for i, doc_embedding in enumerate(self._embeddings):
            dist = self._cosine_distance(query_embedding, doc_embedding)
            distances.append((i, dist))

        distances.sort(key=lambda x: x[1])

        results = []
        for idx, dist in distances[:k]:
            results.append((self._documents[idx], dist))

        return results

    @staticmethod
    def _cosine_distance(vec_a, vec_b):
        """
        Calculate cosine distance between two vectors.

        Cosine distance = 1 - cosine_similarity
        Range: 0.0 (identical) to 2.0 (opposite)

        Args:
            vec_a: First vector (list of floats).
            vec_b: Second vector (list of floats).

        Returns:
            Float distance value.
        """
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        mag_a = math.sqrt(sum(a * a for a in vec_a))
        mag_b = math.sqrt(sum(b * b for b in vec_b))

        if mag_a == 0 or mag_b == 0:
            return 1.0

        similarity = dot_product / (mag_a * mag_b)
        return 1.0 - similarity

    def __len__(self):
        return len(self._documents)
