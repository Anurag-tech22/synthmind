"""Google Gemma 2 / CodeGemma Integration Engine.

Implements lightweight, high-efficiency, privacy-preserving research distillation
using Google's open Gemma foundation models (Gemma 2 27B / 9B).

Used for:
  • Edge & privacy-preserving document distillation
  • High-speed factual extraction
  • Socratic assumption checking
"""

from __future__ import annotations

import logging
from typing import Any

from google import genai
from google.genai import types as genai_types

logger = logging.getLogger("synthmind.gemma")

GEMMA_MODELS = [
    "gemma-4-26b-a4b-it",
    "gemma-4-31b-it",
    "gemma-2-27b-it",
    "gemma-2-9b-it",
]


async def run_gemma_distillation(
    client: genai.Client,
    content: str,
    focus: str = "key_tradeoffs",
    preferred_model: str = "gemma-4-26b-a4b-it",
) -> dict[str, Any]:
    """Run Gemma model for fast factual distillation and edge summarization."""
    if not content or len(content.strip()) < 10:
        return {"summary": "Insufficient content provided.", "model": preferred_model}

    prompt = f"""You are Google Gemma, an open, ultra-efficient AI research assistant.
Analyze and distill the following research text focusing on: {focus}.

Provide:
1. Core Executive Takeaway (2 sentences max)
2. Key Trade-offs / Numerical Facts (bullet points)
3. Confidence & Edge Considerations

Text to analyze:
{content[:4000]}
"""

    last_err = None
    for model_name in [preferred_model] + [m for m in GEMMA_MODELS if m != preferred_model]:
        try:
            logger.info("Executing Gemma distillation with model: %s", model_name)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=1000,
                ),
            )
            if response and response.text:
                return {
                    "summary": response.text,
                    "model_used": model_name,
                    "provider": "Google Gemma Open Models",
                    "status": "success",
                }
        except Exception as exc:
            last_err = exc
            logger.warning("Gemma model %s failed (%s), trying next...", model_name, str(exc)[:80])

    return {
        "summary": f"Gemma distillation completed with fallback context: {content[:300]}...",
        "model_used": "gemma-fallback",
        "error": str(last_err),
        "status": "fallback",
    }
