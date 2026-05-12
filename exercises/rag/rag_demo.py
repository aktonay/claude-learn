"""
RAG Pipeline Demo — Full Comparison
=====================================
Runs 3 retrieval strategies side-by-side on the same queries:

  1. Semantic Only (VectorIndex)  — finds by MEANING
  2. Lexical Only (BM25Index)     — finds by EXACT TERMS
  3. Hybrid (Retriever with RRF)  — combines both via Reciprocal Rank Fusion

Then uses the LLM to generate a final answer from retrieved context.

Test queries designed to expose strengths/weaknesses:
  - "What did the software engineering team do?"  (semantic-heavy)
  - "Find information about INC-2023-Q4-011"      (exact term match)
  - "What was the revenue growth?"                 (general fact)

Run: python rag_demo.py
"""

import os
import sys
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Add current dir for imports
sys.path.insert(0, os.path.dirname(__file__))

from chunking import chunk_by_section
from embeddings import generate_embedding
from vector_store import VectorIndex
from bm25_store import BM25Index
from retriever import Retriever

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

llm_client = OpenAI(
    api_key=os.getenv("ZAI_API_KEY"),
    base_url=os.getenv("ZAI_BASE_URL"),
)

MODEL = "glm-4.5-air"
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "report.md")


# ---------------------------------------------------------------------------
# Test queries — designed to test different search strengths
# ---------------------------------------------------------------------------
QUERIES = [
    {
        "query": "What did the software engineering team accomplish this year?",
        "description": "Semantic-heavy: needs understanding of 'accomplish' → project work",
        "expected_section": "Software Engineering",
    },
    {
        "query": "Find details about incident INC-2023-Q4-011",
        "description": "Lexical-heavy: needs exact match on the incident ID",
        "expected_section": "Cybersecurity",
    },
    {
        "query": "What was the company revenue and how did it grow?",
        "description": "General fact: should find financial section",
        "expected_section": "Financial",
    },
]


# ---------------------------------------------------------------------------
# Build indexes from the report
# ---------------------------------------------------------------------------
def build_indexes(chunks):
    """
    Build all 3 indexes from the same chunks.

    Returns:
        (vector_index, bm25_index, retriever)
    """
    print("  Generating embeddings for all chunks...")
    embeddings = generate_embedding(chunks)

    # 1. Semantic-only index (VectorIndex)
    vector_idx = VectorIndex()
    for chunk, emb in zip(chunks, embeddings):
        vector_idx.add_document({"content": chunk}, embedding=emb)
    print(f"    VectorIndex: {len(vector_idx)} documents")

    # 2. Lexical-only index (BM25Index)
    bm25_idx = BM25Index()
    for chunk in chunks:
        bm25_idx.add_document({"content": chunk})
    print(f"    BM25Index: {len(bm25_idx)} documents")

    # 3. Hybrid retriever (combines both)
    vector_idx2 = VectorIndex()
    for chunk, emb in zip(chunks, embeddings):
        vector_idx2.add_document({"content": chunk}, embedding=emb)

    bm25_idx2 = BM25Index()
    for chunk in chunks:
        bm25_idx2.add_document({"content": chunk})

    retriever = Retriever(vector_idx2, bm25_idx2)
    print(f"    Retriever (Hybrid): {len(retriever)} documents")

    return vector_idx, bm25_idx, retriever


# ---------------------------------------------------------------------------
# Pre-compute all query embeddings in one batch call to avoid rate limits
# ---------------------------------------------------------------------------
def precompute_query_embeddings(queries):
    """
    Embed all queries at once to minimize API calls.
    VoyageAI free tier: 3 RPM. Batch everything into 1 call.
    """
    query_texts = [q["query"] for q in queries]
    print(f"  Pre-computing embeddings for {len(query_texts)} queries (1 batch call)...")
    embeddings = generate_embedding(query_texts, input_type="query")
    return dict(zip(query_texts, embeddings))


# ---------------------------------------------------------------------------
# Run search comparison (uses pre-computed embeddings, no API calls)
# ---------------------------------------------------------------------------
def compare_searches(query, query_embedding, vector_idx, bm25_idx, retriever, k=3):
    """
    Run the same query against all 3 strategies and compare results.
    Uses pre-computed query embedding to avoid extra API calls.

    Returns:
        Dict with results from each strategy.
    """
    results = {}

    # Semantic search (use pre-computed embedding)
    t0 = time.time()
    semantic_results = vector_idx.search_with_embedding(query_embedding, k=k)
    semantic_time = time.time() - t0
    results["semantic"] = {
        "results": semantic_results,
        "time": semantic_time,
    }

    # BM25 search (no API call, instant)
    t0 = time.time()
    bm25_results = bm25_idx.search(query, k=k)
    bm25_time = time.time() - t0
    results["bm25"] = {
        "results": bm25_results,
        "time": bm25_time,
    }

    # Hybrid search (use pre-computed embedding)
    t0 = time.time()
    hybrid_results = retriever.search_with_embedding(query, query_embedding, k=k)
    hybrid_time = time.time() - t0
    results["hybrid"] = {
        "results": hybrid_results,
        "time": hybrid_time,
    }

    return results


# ---------------------------------------------------------------------------
# Check if the correct section was found
# ---------------------------------------------------------------------------
def section_found(results, expected_section):
    """Check if the expected section appears in top results."""
    for doc, _score in results:
        if expected_section.lower() in doc["content"].lower():
            return True
    return False


# ---------------------------------------------------------------------------
# Generate final answer from retrieved context
# ---------------------------------------------------------------------------
def generate_answer(query, context_chunks):
    """
    Use the LLM to generate an answer from retrieved context.

    This is the final step of RAG: retrieved chunks + query → answer.
    """
    context = "\n\n---\n\n".join(context_chunks)

    messages = [
        {"role": "user", "content": (
            f"Answer the user's question using ONLY the provided context. "
            f"If the context doesn't contain the answer, say so.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {query}\n\n"
            f"Answer:"
        )}
    ]

    response = llm_client.chat.completions.create(
        model=MODEL,
        max_tokens=500,
        messages=messages,
    )

    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Main: run full comparison and save log
# ---------------------------------------------------------------------------
def run_full_demo():
    """Run the complete RAG comparison pipeline."""

    print("=" * 70)
    print("  RAG PIPELINE — SEMANTIC vs LEXICAL vs HYBRID SEARCH")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

    # Step 1: Load and chunk document
    print("  Step 1: Loading and chunking document...")
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = chunk_by_section(text)
    print(f"    Created {len(chunks)} chunks from report.md")
    print()

    # Step 2: Build indexes
    print("  Step 2: Building search indexes...")
    vector_idx, bm25_idx, retriever = build_indexes(chunks)
    print()

    # Step 2b: Pre-compute all query embeddings in ONE batch call
    query_embeddings = precompute_query_embeddings(QUERIES)
    print()

    # Step 3: Run comparison queries
    print("  Step 3: Running search comparisons (no API calls needed now)...")
    print()

    all_comparisons = []

    for i, q in enumerate(QUERIES, 1):
        print(f"  Query {i}: {q['query']}")
        print(f"  ({q['description']})")
        print(f"  Expected section: {q['expected_section']}")
        print()

        query_emb = query_embeddings[q["query"]]
        results = compare_searches(q["query"], query_emb, vector_idx, bm25_idx, retriever)

        # Check accuracy: did each strategy find the right section?
        accuracy = {
            "semantic": section_found(results["semantic"]["results"], q["expected_section"]),
            "bm25": section_found(results["bm25"]["results"], q["expected_section"]),
            "hybrid": section_found(results["hybrid"]["results"], q["expected_section"]),
        }

        # Generate final answer using hybrid results (best of both worlds)
        hybrid_docs = [doc for doc, _score in results["hybrid"]["results"]]
        answer = generate_answer(q["query"], [d["content"] for d in hybrid_docs])

        # Print results
        for strategy_name in ["semantic", "bm25", "hybrid"]:
            r = results[strategy_name]
            hit = "HIT" if accuracy[strategy_name] else "MISS"
            print(f"    {strategy_name.upper():12s} [{hit}] ({r['time']:.3f}s)")
            for j, (doc, score) in enumerate(r["results"][:2], 1):
                preview = doc["content"][:80].replace("\n", " ")
                print(f"      {j}. [{score:.4f}] {preview}...")
            print()

        print(f"  LLM Answer: {answer[:200]}...")
        print()

        all_comparisons.append({
            "query": q,
            "results": results,
            "accuracy": accuracy,
            "answer": answer,
        })

    # Step 4: Save log
    filepath = save_log(all_comparisons, chunks)
    return filepath


# ---------------------------------------------------------------------------
# Save formatted log
# ---------------------------------------------------------------------------
def save_log(all_comparisons, chunks):
    """Save detailed comparison results to log file."""
    os.makedirs(LOGS_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = os.path.join(LOGS_DIR, f"rag_comparison_{timestamp}.txt")

    sep = "=" * 70
    lines = []

    # Header
    lines.append(sep)
    lines.append("  RAG PIPELINE COMPARISON")
    lines.append("  Semantic vs Lexical vs Hybrid Search")
    lines.append(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(sep)
    lines.append("")

    # Pipeline explanation
    lines.append("  THE RAG PIPELINE:")
    lines.append("-" * 70)
    lines.append("")
    lines.append("  Step 1: CHUNK the document into smaller pieces")
    lines.append("  Step 2: EMBED each chunk (text -> numbers via VoyageAI)")
    lines.append("  Step 3: STORE embeddings in a vector database")
    lines.append("  Step 4: EMBED the user's query")
    lines.append("  Step 5: SEARCH for most similar chunks")
    lines.append("  Step 6: GENERATE answer from top chunks + query via LLM")
    lines.append("")
    lines.append("  THREE SEARCH STRATEGIES COMPARED:")
    lines.append("")
    lines.append("  +------------+--------------------------------+--------------------------------+")
    lines.append("  | Strategy   | Strength                       | Weakness                       |")
    lines.append("  +------------+--------------------------------+--------------------------------+")
    lines.append("  | Semantic   | Understands MEANING/CONTEXT    | Misses exact term matches      |")
    lines.append("  | (Vector)   | 'accomplish' -> project work   | 'INC-2023-Q4-011' -> ?         |")
    lines.append("  +------------+--------------------------------+--------------------------------+")
    lines.append("  | Lexical    | Finds EXACT TERM matches       | No understanding of synonyms   |")
    lines.append("  | (BM25)     | 'INC-2023-Q4-011' -> found!    | 'accomplish' != 'achieved'     |")
    lines.append("  +------------+--------------------------------+--------------------------------+")
    lines.append("  | Hybrid     | BEST of both via RRF fusion    | More complex to implement      |")
    lines.append("  | (Retriever)| Meaning + exact matches        | Two indexes to maintain        |")
    lines.append("  +------------+--------------------------------+--------------------------------+")
    lines.append("")
    lines.append("  RECIPROCAL RANK FUSION (RRF):")
    lines.append("  RRF_score(doc) = sum( 1 / (k + rank) ) for each index")
    lines.append("  Merges ranked lists without needing score normalization.")
    lines.append("  Docs that rank well in MULTIPLE indexes get boosted.")
    lines.append("")

    # Chunks created
    lines.append(sep)
    lines.append("  DOCUMENT CHUNKS")
    lines.append(sep)
    lines.append("")
    for i, chunk in enumerate(chunks):
        preview = chunk[:120].replace("\n", " ")
        lines.append(f"  Chunk {i+1} ({len(chunk)} chars): {preview}...")
    lines.append("")

    # Each query comparison
    for i, comp in enumerate(all_comparisons, 1):
        q = comp["query"]
        results = comp["results"]
        accuracy = comp["accuracy"]

        lines.append(sep)
        lines.append(f"  QUERY {i}: {q['query']}")
        lines.append(f"  Type: {q['description']}")
        lines.append(f"  Expected section: {q['expected_section']}")
        lines.append(sep)
        lines.append("")

        for strategy_name in ["semantic", "bm25", "hybrid"]:
            r = results[strategy_name]
            hit = "HIT" if accuracy[strategy_name] else "MISS"
            label = {
                "semantic": "SEMANTIC (VectorIndex — cosine similarity)",
                "bm25": "LEXICAL (BM25Index — keyword matching)",
                "hybrid": "HYBRID (Retriever — RRF fusion)",
            }[strategy_name]

            lines.append(f"  {label}")
            lines.append(f"  Accuracy: {hit}  |  Time: {r['time']:.4f}s")
            lines.append("")

            for j, (doc, score) in enumerate(r["results"], 1):
                score_label = "cosine distance" if strategy_name != "hybrid" else "RRF score"
                lines.append(f"    Result {j} [{score_label}: {score:.4f}]:")
                content_preview = doc["content"][:200].replace("\n", " ")
                lines.append(f"      {content_preview}...")
                lines.append("")

            lines.append("")

        # Final answer
        lines.append("  FINAL LLM ANSWER (generated from Hybrid results):")
        lines.append(f"    {comp['answer']}")
        lines.append("")

    # Summary table
    lines.append(sep)
    lines.append("  SUMMARY — WHICH STRATEGY IS BEST?")
    lines.append(sep)
    lines.append("")
    lines.append("  | # | Query                                | Semantic | BM25 | Hybrid |")
    lines.append("  |---|--------------------------------------|----------|------|--------|")

    for i, comp in enumerate(all_comparisons, 1):
        q_short = comp["query"]["query"][:36]
        s = "HIT" if comp["accuracy"]["semantic"] else "MISS"
        b = "HIT" if comp["accuracy"]["bm25"] else "MISS"
        h = "HIT" if comp["accuracy"]["hybrid"] else "MISS"
        lines.append(f"  | {i} | {q_short:<36s} | {s:8s} | {b:4s} | {h:6s} |")

    lines.append("")
    lines.append("  CONCLUSION:")
    lines.append("")
    lines.append("  Semantic search excels at understanding INTENT:")
    lines.append("    'What did the team accomplish?' -> finds project work sections")
    lines.append("    Even though 'accomplish' never appears in the document.")
    lines.append("")
    lines.append("  BM25 excels at EXACT TERM matching:")
    lines.append("    'INC-2023-Q4-011' -> finds the exact section with that ID")
    lines.append("    Semantic search might miss this because the ID is opaque.")
    lines.append("")
    lines.append("  Hybrid (RRF) gets the BEST of both:")
    lines.append("    Documents that rank well in BOTH indexes get boosted.")
    lines.append("    This is the standard approach in production RAG systems.")
    lines.append("")
    lines.append("  WHY HYBRID IS BETTER (mathematically):")
    lines.append("    RRF_score = sum( 1/(k + rank_i) ) for each index i")
    lines.append("    A doc at rank 1 in BOTH indexes:  1/61 + 1/61 = 0.0328")
    lines.append("    A doc at rank 1 in ONE index:      1/61 + 1/62 = 0.0322")
    lines.append("    Consistently relevant docs always win over one-hit wonders.")
    lines.append("")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filepath


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    filepath = run_full_demo()
    print()
    print(f"  Full results saved to: {filepath}")
