"""
Text Chunking Strategies
=========================
Breaking documents into smaller pieces is the first step in any RAG pipeline.
The chunking strategy you choose directly affects retrieval quality.

Four strategies implemented here:

1. chunk_by_chars()   — fixed-size character windows with overlap
2. chunk_by_sentence() — sentence-boundary splitting with grouping
3. chunk_by_section()  — split on markdown headers (## )
4. chunk_semantic()    — group sentences by embedding similarity

Trade-offs:
  Size-based:     Simple, reliable, works with ANY text. But cuts mid-sentence.
  Sentence-based: Preserves sentence boundaries. Good middle ground.
  Section-based:  Cleanest chunks. Only works with structured documents.
  Semantic:       Best quality. Most expensive (needs embedding model).

For production: size-based with overlap is the default go-to.
For structured docs: section-based gives the cleanest results.
"""

import re
import voyageai


# ---------------------------------------------------------------------------
# Strategy 1: Character-based chunking with overlap
# ---------------------------------------------------------------------------
# The simplest approach: slide a fixed-size window over the text.
# Overlap ensures context isn't lost at chunk boundaries.
# Works with ANY text type (code, prose, logs, etc.)

def chunk_by_chars(text, chunk_size=300, chunk_overlap=50):
    """
    Split text into fixed-size character chunks with overlap.

    Args:
        text: Input text string.
        chunk_size: Number of characters per chunk.
        chunk_overlap: Number of overlapping characters between chunks.

    Returns:
        List of chunk strings.
    """
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])

        # Move forward by (chunk_size - overlap)
        # If we're at the end, stop
        if end == len(text):
            break
        start = end - chunk_overlap

    return chunks


# ---------------------------------------------------------------------------
# Strategy 2: Sentence-based chunking
# ---------------------------------------------------------------------------
# Split on sentence boundaries (., !, ?) then group into chunks.
# Better than character-based because it preserves complete sentences.
# Still a "dumb" approach — doesn't understand section boundaries.

def chunk_by_sentence(text, max_sentences=3, overlap=1):
    """
    Split text into chunks of N sentences with overlap.

    Args:
        text: Input text string.
        max_sentences: Max sentences per chunk.
        overlap: How many sentences to overlap between chunks.

    Returns:
        List of chunk strings.
    """
    # Split on sentence-ending punctuation followed by whitespace
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    # Filter empty sentences
    sentences = [s for s in sentences if s.strip()]

    chunks = []
    start = 0

    while start < len(sentences):
        end = min(start + max_sentences, len(sentences))
        chunk = " ".join(sentences[start:end])
        chunks.append(chunk)

        step = max_sentences - overlap
        if step <= 0:
            step = 1
        start += step

    return chunks


# ---------------------------------------------------------------------------
# Strategy 3: Section-based chunking (markdown headers)
# ---------------------------------------------------------------------------
# Split on "## " headers. Each chunk is a complete section.
# Best quality chunks — but ONLY works with structured documents.
# If your document has no headers, this falls back to one giant chunk.

def chunk_by_section(text):
    """
    Split markdown text on ## headers.

    Args:
        text: Markdown-formatted text.

    Returns:
        List of section strings (each includes its header).
    """
    # Split on newline followed by ## 
    parts = re.split(r"(?=\n## )", text)
    # Clean up and filter empty parts
    chunks = []
    for part in parts:
        part = part.strip()
        if part:
            chunks.append(part)
    return chunks


# ---------------------------------------------------------------------------
# Strategy 4: Semantic chunking (embedding-based)
# ---------------------------------------------------------------------------
# The most sophisticated approach:
#   1. Split text into individual sentences
#   2. Embed each sentence
#   3. Compare consecutive sentences by cosine similarity
#   4. Start a new chunk when similarity drops below a threshold
#
# This groups related sentences together even if they're far apart
# structurally. Most expensive but produces the most meaningful chunks.

def chunk_semantic(text, similarity_threshold=0.5, model="voyage-3-lite"):
    """
    Split text into chunks based on semantic similarity between sentences.

    Args:
        text: Input text string.
        similarity_threshold: If cosine similarity between consecutive
                             sentences drops below this, start a new chunk.
        model: VoyageAI embedding model to use.

    Returns:
        List of chunk strings.
    """
    vo = voyageai.Client()

    # Split into sentences
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s for s in sentences if s.strip()]

    if len(sentences) <= 1:
        return [text]

    # Embed all sentences at once (batch is faster)
    result = vo.embed(sentences, model=model, input_type="document")
    embeddings = result.embeddings

    # Calculate cosine similarity between consecutive sentences
    def cosine_sim(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = sum(x * x for x in a) ** 0.5
        mag_b = sum(x * x for x in b) ** 0.5
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    # Group sentences into chunks based on similarity
    chunks = []
    current_chunk = [sentences[0]]

    for i in range(1, len(sentences)):
        sim = cosine_sim(embeddings[i - 1], embeddings[i])

        if sim < similarity_threshold:
            # Similarity dropped — save current chunk, start new one
            chunks.append(" ".join(current_chunk))
            current_chunk = [sentences[i]]
        else:
            # Similar enough — add to current chunk
            current_chunk.append(sentences[i])

    # Don't forget the last chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks
