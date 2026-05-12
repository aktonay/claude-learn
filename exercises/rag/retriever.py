"""
Hybrid Retriever — Reciprocal Rank Fusion (RRF)
=================================================
Combines results from multiple search indexes into a single ranked list.

The Problem:
  VectorIndex (semantic) is great at understanding MEANING.
  BM25Index (lexical) is great at finding EXACT term matches.
  Neither is perfect alone. We need to merge their results.

The Solution: Reciprocal Rank Fusion (RRF)
  RRF merges ranked lists from different search methods into one.
  It doesn't care about the actual scores — only the RANK positions.

  Formula: RRF_score(d) = sum( 1 / (k + rank_i(d)) ) for each index i

  Where:
    k = constant (default 60, prevents top ranks from dominating)
    rank_i(d) = rank of document d in index i's results (1-based)

  Example with k=1:
    Doc A ranks #1 in semantic, #2 in BM25:  1/(1+1) + 1/(1+2) = 0.833
    Doc B ranks #3 in semantic, #1 in BM25:  1/(1+3) + 1/(1+1) = 0.750
    Doc C ranks #2 in semantic, #3 in BM25:  1/(1+2) + 1/(1+3) = 0.583

    Final: Doc A wins because it ranked well in BOTH indexes.

Why RRF works:
  - No need to normalize scores across different systems
  - Documents that appear in multiple result sets get boosted
  - Robust to outlier scores from any single index

This is the standard technique used in production RAG systems.
"""

from embeddings import generate_embedding


class Retriever:
    """
    Hybrid retriever that combines multiple search indexes using RRF.

    Usage:
        vector_idx = VectorIndex()
        bm25_idx = BM25Index()

        retriever = Retriever(vector_idx, bm25_idx)
        retriever.add_document({"content": "some text"})
        results = retriever.search("query text", k=3)
    """

    def __init__(self, *indexes):
        """
        Create a retriever from one or more search indexes.

        Args:
            *indexes: One or more index objects with add_document() and search() methods.
        """
        if len(indexes) == 0:
            raise ValueError("At least one index must be provided")
        self._indexes = list(indexes)

    def add_document(self, document, embedding=None):
        """
        Add a document to ALL underlying indexes.

        Args:
            document: Dict with at least a "content" key.
            embedding: Optional pre-computed embedding (for VectorIndex).
        """
        for index in self._indexes:
            # VectorIndex accepts optional embedding, BM25Index ignores it
            if hasattr(index, 'add_document'):
                try:
                    if embedding is not None:
                        index.add_document(document, embedding=embedding)
                    else:
                        index.add_document(document)
                except TypeError:
                    # Some indexes don't accept embedding kwarg
                    index.add_document(document)

    def search(self, query_text, k=3, k_rrf=60):
        """
        Search all indexes and merge results using Reciprocal Rank Fusion.

        Args:
            query_text: The search query.
            k: Number of final results to return.
            k_rrf: RRF constant (default 60). Higher = more smoothing.

        Returns:
            List of (document, rrf_score) tuples sorted by score (highest first).
        """
        fetch_k = max(k * 3, 10)
        all_results = []
        for index in self._indexes:
            results = index.search(query_text, k=fetch_k)
            all_results.append(results)
        return self._fuse(all_results, k, k_rrf)

    def search_with_embedding(self, query_text, query_embedding, k=3, k_rrf=60):
        """
        Search all indexes using a pre-computed query embedding.
        Avoids duplicate embedding API calls (important for rate-limited tiers).

        Args:
            query_text: The search query string (for BM25).
            query_embedding: Pre-computed embedding (for VectorIndex).
            k: Number of final results to return.
            k_rrf: RRF constant.

        Returns:
            List of (document, rrf_score) tuples sorted by score (highest first).
        """
        fetch_k = max(k * 3, 10)
        all_results = []
        for index in self._indexes:
            # VectorIndex has search_with_embedding, BM25Index doesn't
            if hasattr(index, 'search_with_embedding'):
                results = index.search_with_embedding(query_embedding, k=fetch_k)
            else:
                results = index.search(query_text, k=fetch_k)
            all_results.append(results)
        return self._fuse(all_results, k, k_rrf)

    def _fuse(self, all_results, k, k_rrf):
        """
        Apply Reciprocal Rank Fusion to merge results from multiple indexes.
        """
        rrf_scores = {}

        for index_results in all_results:
            for rank, (doc, _distance) in enumerate(index_results):
                doc_key = doc["content"][:200]

                if doc_key not in rrf_scores:
                    rrf_scores[doc_key] = {"doc": doc, "score": 0.0}

                rrf_scores[doc_key]["score"] += 1.0 / (k_rrf + rank + 1)

        sorted_results = sorted(
            rrf_scores.values(),
            key=lambda x: x["score"],
            reverse=True,
        )

        return [(item["doc"], item["score"]) for item in sorted_results[:k]]

    def __len__(self):
        return max(len(idx) for idx in self._indexes)
