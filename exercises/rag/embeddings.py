"""
Embedding Generation with VoyageAI
====================================
Converts text into numerical vectors (embeddings) that capture semantic meaning.

How embeddings work:
  1. Feed text into an embedding model (VoyageAI)
  2. Model outputs a list of floats (e.g., 1024 numbers)
  3. Similar text → similar numbers → can find with math (cosine similarity)

Why VoyageAI:
  - Anthropic doesn't provide embedding models
  - VoyageAI is the recommended embedding provider for Claude/RAG projects
  - voyage-3-large: best quality (1024 dims)
  - voyage-3-lite: faster, cheaper (512 dims), good for demos

The embedding function handles both single strings and lists of strings.
Batch processing is more efficient — fewer API calls.
"""

import os
import voyageai
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Default model: voyage-3-lite is fast and cheap for demos
# Switch to "voyage-3-large" or "voyage-4-large" for production quality
DEFAULT_MODEL = "voyage-3-lite"

_client = None


def _get_client():
    """Lazy-init VoyageAI client (only created when first needed)."""
    global _client
    if _client is None:
        _client = voyageai.Client()
    return _client


def generate_embedding(text, model=None, input_type="document"):
    """
    Generate an embedding vector for text.

    Args:
        text: A single string or a list of strings to embed.
        model: VoyageAI model name. Default: voyage-3-lite.
        input_type: "document" for stored chunks, "query" for search queries.

    Returns:
        If text is a string: returns a single embedding (list of floats).
        If text is a list: returns a list of embeddings.

    Example:
        >>> emb = generate_embedding("hello world")
        >>> len(emb)
        512

        >>> embs = generate_embedding(["hello", "world"])
        >>> len(embs)
        2
    """
    if model is None:
        model = DEFAULT_MODEL

    vo = _get_client()

    # Handle single string vs list
    if isinstance(text, str):
        result = vo.embed([text], model=model, input_type=input_type)
        return result.embeddings[0]
    else:
        result = vo.embed(text, model=model, input_type=input_type)
        return result.embeddings


def get_embedding_dimension(model=None):
    """Return the embedding dimension for a given model."""
    if model is None:
        model = DEFAULT_MODEL
    # Quick embed to check dimension
    emb = generate_embedding("test", model=model)
    return len(emb)
