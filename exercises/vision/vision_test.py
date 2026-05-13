"""
Vision API Exercise
===================
Demonstrates how to send images to the model for analysis.
Uses the OpenAI-compatible image format with the ZAI API.

Vision-capable models on ZAI: glm-5, glm-5-turbo
Non-vision models: glm-4.5, glm-4.5-air, glm-5.1

How images work:
  - Images are sent as base64-encoded data in the message content
  - You can mix image blocks and text blocks in a single message
  - Each image counts as tokens based on dimensions: tokens = (w x h) / 750
  - Same prompt engineering techniques apply to images as text

This exercise:
  1. Creates test images (simple colored shapes)
  2. Sends them to the model with different prompt styles
  3. Shows how prompt engineering improves image analysis
  4. Saves results to logs/

NOTE: This exercise requires a vision-capable model (glm-5 or glm-5-turbo).
      glm-4.5-air does NOT support images and will return an error.
"""

import os
import sys
import base64
import io
import json
import time
import struct
import zlib
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

client = OpenAI(
    api_key=os.getenv("ZAI_API_KEY"),
    base_url=os.getenv("ZAI_BASE_URL"),
)

VISION_MODEL = "glm-5-turbo"
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")

# ===================================================================
# CHECK FOR REAL IMAGES
# ===================================================================
# The ZAI vision API needs real image files to analyze.
# Place .png or .jpg files in the images/ subfolder to run tests.
# If no images found, the exercise skips with instructions.

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "images")


# ===================================================================
# IMAGE LOADING (real images from disk)
# ===================================================================

def load_image_b64(filepath):
    """Load an image file and return base64-encoded string."""
    with open(filepath, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def get_media_type(filepath):
    """Get MIME type from file extension."""
    ext = os.path.splitext(filepath)[1].lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(ext, "image/png")


def find_test_images():
    """Find all images in the images/ folder. Returns list of (path, label)."""
    if not os.path.isdir(IMAGES_DIR):
        return []
    results = []
    for f in sorted(os.listdir(IMAGES_DIR)):
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
            results.append((os.path.join(IMAGES_DIR, f), f))
    return results


def make_image_url(b64_data, media_type="image/png"):
    """Create an image_url content block for the OpenAI-compatible API."""
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{media_type};base64,{b64_data}"},
    }


def make_text_block(text):
    """Create a text content block."""
    return {"type": "text", "text": text}


# ===================================================================
# CHAT FUNCTION (vision-capable)
# ===================================================================

def chat_vision(content_blocks, model=VISION_MODEL, max_tokens=500):
    """Send a message with image + text content blocks."""
    resp = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": content_blocks}],
        extra_body={"thinking": {"type": "disabled"}},
    )
    return {
        "content": resp.choices[0].message.content or "",
        "tokens": resp.usage.completion_tokens if resp.usage else 0,
        "finish_reason": resp.choices[0].finish_reason,
    }


# ===================================================================
# TEST 1: BASIC DESCRIPTION
# ===================================================================

def test_basic_description(images):
    """Send each image with a simple description prompt."""
    results = []
    for filepath, label in images:
        b64 = load_image_b64(filepath)
        media = get_media_type(filepath)
        r = chat_vision([
            make_image_url(b64, media),
            make_text_block("Describe what you see in this image in 2-3 sentences."),
        ])
        results.append({"file": label, "response": r["content"], "tokens": r["tokens"]})
    return results


# ===================================================================
# TEST 2: NAIVE vs STRUCTURED PROMPT
# ===================================================================

def test_prompt_engineering(images):
    """Compare naive vs structured prompts on the first image."""
    if not images:
        return None

    filepath, label = images[0]
    b64 = load_image_b64(filepath)
    media = get_media_type(filepath)

    naive_prompt = "What's in this image?"
    structured_prompt = """Analyze this image step by step:

1. Identify the main subject or objects in the image.
2. Describe the colors, textures, and composition.
3. Note any text, labels, or distinctive features.
4. Describe the overall context or setting.
5. Rate the image quality (resolution, lighting, clarity) on a scale of 1-5.

Provide a structured analysis."""

    naive = chat_vision([make_image_url(b64, media), make_text_block(naive_prompt)])
    structured = chat_vision([make_image_url(b64, media), make_text_block(structured_prompt)])

    return {
        "file": label,
        "naive": {"prompt": naive_prompt, "response": naive["content"], "tokens": naive["tokens"]},
        "structured": {"prompt": structured_prompt, "response": structured["content"], "tokens": structured["tokens"]},
    }


# ===================================================================
# TEST 3: COMPARISON BETWEEN IMAGES
# ===================================================================

def test_image_comparison(images):
    """Compare two images side by side (if available)."""
    if len(images) < 2:
        return None

    fp1, label1 = images[0]
    fp2, label2 = images[1]
    b64_1 = load_image_b64(fp1)
    b64_2 = load_image_b64(fp2)
    media1 = get_media_type(fp1)
    media2 = get_media_type(fp2)

    r = chat_vision([
        make_image_url(b64_1, media1),
        make_image_url(b64_2, media2),
        make_text_block(f"""Compare these two images systematically:

1. Describe Image 1 (first image).
2. Describe Image 2 (second image).
3. List the key similarities between them.
4. List the key differences between them.
5. Which image appears more professional/higher quality and why?

Image 1 filename: {label1}
Image 2 filename: {label2}"""),
    ], max_tokens=1000)

    return {
        "image1": label1,
        "image2": label2,
        "response": r["content"],
        "tokens": r["tokens"],
    }


# ===================================================================
# SAVE TXT REPORT
# ===================================================================

def save_report(test1, test2, test3):
    os.makedirs(LOGS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = os.path.join(LOGS_DIR, f"vision_test_{timestamp}.txt")

    sep = "=" * 70
    dash = "-" * 70
    lines = []

    lines.append(sep)
    lines.append("  VISION API TEST REPORT")
    lines.append(f"  Date: {timestamp}")
    lines.append(f"  Model: {VISION_MODEL}")
    lines.append(sep)
    lines.append("")

    lines.append(sep)
    lines.append("  TEST 1: BASIC DESCRIPTION")
    lines.append(sep)
    lines.append("")
    if test1:
        for r in test1:
            lines.append(f"  File: {r['file']}")
            lines.append(f"  Tokens: {r['tokens']}")
            lines.append("  Response:")
            for tl in r["response"].split("\n"):
                lines.append(f"    {tl}")
            lines.append("")
    else:
        lines.append("  No images provided.")
        lines.append("")

    lines.append(sep)
    lines.append("  TEST 2: NAIVE vs STRUCTURED PROMPT")
    lines.append(sep)
    lines.append("")
    if test2:
        lines.append(f"  Image: {test2['file']}")
        lines.append("")
        lines.append(dash)
        lines.append("  NAIVE PROMPT:")
        lines.append(f'  "{test2["naive"]["prompt"]}"')
        lines.append(dash)
        for tl in test2["naive"]["response"].split("\n"):
            lines.append(f"  {tl}")
        lines.append(f"  Tokens: {test2['naive']['tokens']}")
        lines.append("")
        lines.append(dash)
        lines.append("  STRUCTURED PROMPT:")
        for tl in test2["structured"]["prompt"].split("\n")[:5]:
            lines.append(f"  {tl}")
        lines.append(dash)
        for tl in test2["structured"]["response"].split("\n"):
            lines.append(f"  {tl}")
        lines.append(f"  Tokens: {test2['structured']['tokens']}")
    else:
        lines.append("  No images provided.")
    lines.append("")

    lines.append(sep)
    lines.append("  TEST 3: IMAGE COMPARISON")
    lines.append(sep)
    lines.append("")
    if test3:
        lines.append(f"  Image 1: {test3['image1']}")
        lines.append(f"  Image 2: {test3['image2']}")
        lines.append(f"  Tokens: {test3['tokens']}")
        lines.append("  Response:")
        for tl in test3["response"].split("\n"):
            lines.append(f"    {tl}")
    else:
        lines.append("  Need at least 2 images for comparison.")
    lines.append("")

    lines.append(sep)
    lines.append("  KEY TAKEAWAYS")
    lines.append(sep)
    lines.append("")
    lines.append("  1. IMAGE FORMAT: Images sent as base64 in content array with text blocks.")
    lines.append("  2. TOKEN COST: Each image costs tokens = (width x height) / 750")
    lines.append("  3. PROMPT ENGINEERING APPLIES TO IMAGES:")
    lines.append("     - Naive: 'What's in this image?' -> vague")
    lines.append("     - Structured: step-by-step methodology -> detailed, accurate")
    lines.append("  4. VISION MODELS ON ZAI: glm-5, glm-5-turbo support images")
    lines.append("  5. LIMITATIONS: 100 images/request, 5MB/image, 8000px max")

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
    print(f"  VISION API EXERCISE (model: {VISION_MODEL})")
    print("=" * 60)
    print()

    images = find_test_images()

    if not images:
        print("  No images found in exercises/vision/images/")
        print()
        print("  To run this exercise:")
        print("    1. Create folder: exercises/vision/images/")
        print("    2. Place .png or .jpg files in it")
        print("    3. Run this script again")
        print()
        print("  Vision-capable models: glm-5, glm-5-turbo")
        print("  Non-vision models: glm-4.5, glm-4.5-air, glm-5.1")
        print()
        print("  The code is ready — it just needs real images to analyze.")
        sys.exit(0)

    print(f"  Found {len(images)} image(s):")
    for _, label in images:
        print(f"    - {label}")
    print()

    print("  [1/3] Basic description test...")
    test1 = test_basic_description(images)
    for r in test1:
        preview = r["response"][:80].replace("\n", " ")
        print(f"        {r['file']}: {preview}...")
    print()

    print("  [2/3] Naive vs structured prompt...")
    test2 = test_prompt_engineering(images)
    if test2:
        print(f"        Naive:      {test2['naive']['response'][:60]}...")
        print(f"        Structured: {test2['structured']['response'][:60]}...")
    print()

    print("  [3/3] Image comparison...")
    test3 = test_image_comparison(images)
    if test3:
        print(f"        {test3['image1']} vs {test3['image2']}: {test3['response'][:60]}...")
    else:
        print("        Skipped (need 2+ images)")
    print()

    filepath = save_report(test1, test2, test3)
    print(f"  Report saved to: {filepath}")
