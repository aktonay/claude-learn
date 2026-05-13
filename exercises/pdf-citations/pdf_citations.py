"""
PDF + Citations Exercise
========================
Demonstrates document processing with citations using two approaches:

1. PROMPT-BASED CITATIONS (works with any model):
   - Ingest document text in the prompt using XML tags
   - Ask the model to cite exact source text inline
   - Parse citations from the response
   - Portable across all models and APIs

2. NATIVE PDF + CITATIONS (Anthropic Claude API only):
   - Uses the Anthropic document type with base64-encoded PDFs
   - API returns structured citation objects with page numbers
   - More powerful but requires Claude API + real PDF files

Since the ZAI OpenAI-compatible API does not support native document
uploads or structured citations, this exercise uses approach #1.

The prompt-based approach teaches the core concepts:
  - How to structure document content in prompts
  - How to request inline citations
  - How to parse and validate citations
  - How to build transparency into AI responses

To test with real PDFs: place .pdf files in the documents/ folder.
The exercise will extract text and process it.
"""

import os
import sys
import json
import re
import time
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

client = OpenAI(
    api_key=os.getenv("ZAI_API_KEY"),
    base_url=os.getenv("ZAI_BASE_URL"),
)

MODEL = "glm-4.5-air"
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
DOCS_DIR = os.path.join(os.path.dirname(__file__), "documents")


# ===================================================================
# SAMPLE DOCUMENTS (built-in for testing without real PDFs)
# ===================================================================

SAMPLE_DOCUMENTS = {
    "earth_article": {
        "title": "Earth - Wikipedia Summary",
        "content": """Earth is the third planet from the Sun and the only astronomical object known to harbor life. About 29.2% of Earth's surface is land consisting of continents and islands. The remaining 70.8% is covered with water.

Earth's atmosphere is composed of 78% nitrogen, 21% oxygen, and trace amounts of other gases. The atmosphere protects life on Earth by absorbing ultraviolet solar radiation, warming the surface through heat retention, and reducing temperature extremes between day and night.

Earth formed approximately 4.54 billion years ago. Within the first billion years, life appeared in the oceans and began to affect the atmosphere and surface, leading to the proliferation of anaerobic and later aerobic organisms.

The Moon is Earth's only natural satellite. It is the largest and most massive natural satellite in the Solar System relative to the size of its planet. It stabilizes Earth's axial tilt, which gradually affects climate patterns.

Earth's gravity interacts with other objects in space, especially the Moon, which is Earth's only natural satellite. Earth orbits around the Sun in about 365.25 days.""",
        "source_type": "text",
    },
    "climate_report": {
        "title": "Climate Change Summary Report",
        "content": """Global average temperature has increased by about 1.1 degrees Celsius since the pre-industrial period (1850-1900). This warming is primarily driven by human activities, particularly the emission of greenhouse gases.

Carbon dioxide concentrations in the atmosphere have risen from approximately 280 ppm in 1750 to over 420 ppm in 2024. This increase is largely due to fossil fuel combustion, deforestation, and industrial processes.

Sea levels have risen by approximately 20 centimeters since 1900, with the rate of rise accelerating in recent decades. Projections suggest a further rise of 30-110 cm by 2100 depending on emission scenarios.

The Arctic has warmed at roughly twice the global average rate. Arctic sea ice extent has declined by about 13% per decade since satellite observations began in 1979.

Extreme weather events, including heatwaves, heavy precipitation, and droughts, have become more frequent and intense in many regions. The economic cost of climate-related disasters has increased fivefold over the past 50 years.""",
        "source_type": "text",
    },
}

QUESTIONS = [
    "How did Earth form and what is its atmosphere made of?",
    "What are the main causes and effects of climate change according to the report?",
]


# ===================================================================
# CHAT HELPER
# ===================================================================

def chat(messages, max_tokens=1500):
    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=messages,
        extra_body={"thinking": {"type": "disabled"}},
    )
    return resp.choices[0].message.content or ""


# ===================================================================
# APPROACH 1: NO CITATIONS (baseline)
# ===================================================================

def ask_without_citations(document, question):
    prompt = f"""Based on the following document, answer the question.

<document>
{document}
</document>

Question: {question}"""

    return chat([{"role": "user", "content": prompt}])


# ===================================================================
# APPROACH 2: PROMPT-BASED CITATIONS
# ===================================================================

def ask_with_citations(document, doc_title, question):
    prompt = f"""Based on the following document, answer the question.

<document title="{doc_title}">
{document}
</document>

Question: {question}

IMPORTANT: For each claim in your answer, cite the exact source text from the document.
Use this format for inline citations: [source: "exact quoted text from the document"]
Every factual claim must have a citation. Do not add information not found in the document."""

    return chat([{"role": "user", "content": prompt}])


# ===================================================================
# CITATION PARSER
# ===================================================================

def parse_citations(response_text):
    """Extract all [source: "..."] citations from a response."""
    pattern = r'\[source:\s*"([^"]+)"\]'
    matches = re.findall(pattern, response_text)
    return matches


def validate_citations(citations, source_document):
    """Check if each cited text actually exists in the source document."""
    results = []
    for cited in citations:
        found = cited.lower().strip() in source_document.lower()
        results.append({"cited_text": cited[:100], "verified": found})
    return results


# ===================================================================
# APPROACH 3: STRUCTURED CITATION OUTPUT (JSON)
# ===================================================================

def ask_structured_citations(document, doc_title, question):
    prompt = f"""Based on the following document, answer the question.

<document title="{doc_title}">
{document}
</document>

Question: {question}

Output ONLY raw valid JSON. No markdown. No backticks. Start with [ end with ].
Return an array of claims, each with:
- "claim": the factual claim you are making
- "source": the exact text from the document that supports this claim
- "confidence": your confidence in the claim (high/medium/low)

Example:
[{{"claim": "Earth is the third planet", "source": "Earth is the third planet from the Sun", "confidence": "high"}}]"""

    text = chat([{"role": "user", "content": prompt}], max_tokens=2000)
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return None


# ===================================================================
# TXT REPORT
# ===================================================================

def save_report(results, timestamp_str):
    os.makedirs(LOGS_DIR, exist_ok=True)
    filepath = os.path.join(LOGS_DIR, f"pdf_citations_{timestamp_str}.txt")

    sep = "=" * 70
    dash = "-" * 70
    lines = []

    lines.append(sep)
    lines.append("  PDF + CITATIONS EXERCISE REPORT")
    lines.append(f"  Date: {timestamp_str}")
    lines.append(f"  Model: {MODEL}")
    lines.append(sep)
    lines.append("")

    lines.append(sep)
    lines.append("  APPROACH COMPARISON")
    lines.append(sep)
    lines.append("")
    lines.append("  1. NO CITATIONS (baseline): Direct answer, no source tracking")
    lines.append("  2. PROMPT-BASED CITATIONS: Inline [source: \"...\"] format")
    lines.append("  3. STRUCTURED JSON CITATIONS: Array of {claim, source, confidence}")
    lines.append("")

    for r in results:
        doc_title = r["doc_title"]
        question = r["question"]

        lines.append(sep)
        lines.append(f"  Document: {doc_title}")
        lines.append(f"  Question: {question}")
        lines.append(sep)
        lines.append("")

        lines.append(dash)
        lines.append("  APPROACH 1: NO CITATIONS (baseline)")
        lines.append(dash)
        lines.append("")
        for tl in r["no_citations"].split("\n"):
            lines.append(f"  {tl}")
        lines.append("")

        lines.append(dash)
        lines.append("  APPROACH 2: PROMPT-BASED CITATIONS")
        lines.append(dash)
        lines.append("")
        for tl in r["with_citations"]["response"].split("\n"):
            lines.append(f"  {tl}")
        lines.append("")
        lines.append(f"  Citations found: {len(r['with_citations']['citations'])}")
        for c in r["with_citations"]["validation"]:
            status = "VERIFIED" if c["verified"] else "NOT FOUND"
            lines.append(f"    [{status}] \"{c['cited_text'][:80]}...\"")
        lines.append("")

        lines.append(dash)
        lines.append("  APPROACH 3: STRUCTURED JSON CITATIONS")
        lines.append(dash)
        lines.append("")
        if r["structured_citations"]:
            for item in r["structured_citations"]:
                lines.append(f"  Claim:      {item.get('claim', 'N/A')[:80]}")
                lines.append(f"  Source:     {item.get('source', 'N/A')[:80]}")
                lines.append(f"  Confidence: {item.get('confidence', 'N/A')}")
                lines.append("")
        else:
            lines.append("  (parsing failed)")
            lines.append("")

    lines.append(sep)
    lines.append("  KEY TAKEAWAYS")
    lines.append(sep)
    lines.append("")
    lines.append("  1. CITATIONS BUILD TRUST:")
    lines.append("     Without citations, users can't verify where info comes from.")
    lines.append("     With citations, every claim traces back to source material.")
    lines.append("")
    lines.append("  2. TWO WAYS TO GET CITATIONS:")
    lines.append("     a) Prompt-based: ask model to cite inline [source: \"...\"]")
    lines.append("        Works with ANY model, ANY API. Parse citations with regex.")
    lines.append("     b) Native API (Anthropic only): structured citation objects")
    lines.append("        Returns page numbers, document index, exact spans.")
    lines.append("")
    lines.append("  3. CITATION VALIDATION:")
    lines.append("     Always verify cited text actually exists in the source.")
    lines.append("     Models sometimes hallucinate or paraphrase citations.")
    lines.append("")
    lines.append("  4. DOCUMENT STRUCTURE:")
    lines.append("     Wrap documents in XML tags: <document title=\"...\">...</document>")
    lines.append("     This helps the model distinguish source from instructions.")
    lines.append("")
    lines.append("  5. PDF PROCESSING:")
    lines.append("     Anthropic API: base64 encode PDF, use type=\"document\"")
    lines.append("     ZAI API: extract text from PDF first, send as text content")
    lines.append("     Both benefit from the same citation prompting techniques.")
    lines.append("")
    lines.append("  6. REAL-WORLD USE CASES:")
    lines.append("     - Insurance: satellite imagery fire risk with source tracking")
    lines.append("     - Legal: contract analysis with clause citations")
    lines.append("     - Medical: literature review with paper citations")
    lines.append("     - Education: reading comprehension with text evidence")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filepath


# ===================================================================
# MAIN
# ===================================================================

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 60)
    print(f"  PDF + CITATIONS EXERCISE (model: {MODEL})")
    print("=" * 60)
    print()

    docs = list(SAMPLE_DOCUMENTS.items())
    all_results = []

    for doc_key, doc_data in docs:
        for question in QUESTIONS:
            if doc_key == "earth_article" and "climate" in question.lower():
                continue
            if doc_key == "climate_report" and "Earth form" in question:
                continue

            print(f"  Document: {doc_data['title']}")
            print(f"  Question: {question}")
            print()

            print("    [1/3] Without citations (baseline)...")
            no_cit = ask_without_citations(doc_data["content"], question)
            print(f"           {no_cit[:80]}...")
            print()

            print("    [2/3] With prompt-based citations...")
            with_cit = ask_with_citations(doc_data["content"], doc_data["title"], question)
            citations = parse_citations(with_cit)
            validation = validate_citations(citations, doc_data["content"])
            verified = sum(1 for v in validation if v["verified"])
            print(f"           {len(citations)} citations, {verified} verified")
            print()

            print("    [3/3] Structured JSON citations...")
            structured = ask_structured_citations(doc_data["content"], doc_data["title"], question)
            if structured:
                print(f"           {len(structured)} structured claims")
            else:
                print("           (parsing failed)")
            print()

            all_results.append({
                "doc_key": doc_key,
                "doc_title": doc_data["title"],
                "question": question,
                "no_citations": no_cit,
                "with_citations": {
                    "response": with_cit,
                    "citations": citations,
                    "validation": validation,
                },
                "structured_citations": structured,
            })

            time.sleep(1)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = save_report(all_results, timestamp)

    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print()
    for r in all_results:
        cits = r["with_citations"]["citations"]
        verified = sum(1 for v in r["with_citations"]["validation"] if v["verified"])
        structured_count = len(r["structured_citations"]) if r["structured_citations"] else 0
        print(f"  {r['doc_title'][:40]:40s} | {len(cits)} inline | {verified} verified | {structured_count} structured")
    print()
    print(f"  Report: {filepath}")
