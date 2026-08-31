"""Google Veo & Lyria Multimodal Synthesis Studio.

Integrates Google's flagship creative models:
  • Google Veo 2 / Veo 3.1: Generates cinematic visual storyboards, video motion prompts,
    and visual executive briefings from synthesized research data.
  • Google Lyria / DeepMind Audio: Generates ambient acoustic research focus soundscapes
    and audio brief cues.
"""

from __future__ import annotations

import logging
from typing import Any

from google import genai
from google.genai import types as genai_types

logger = logging.getLogger("synthmind.veo_studio")

VEO_MODELS = [
    "veo-3.1-generate-preview",
    "veo-3.1-fast-generate-preview",
    "veo-3.1-lite-generate-preview",
    "veo-2.0-generate-video",
]


async def generate_veo_storyboard(
    client: genai.Client,
    research_title: str,
    synthesis_data: dict[str, Any] | list[dict[str, Any]],
    style: str = "cinematic_tech",
) -> dict[str, Any]:
    """Generate a Google Veo Video Briefing Storyboard & Motion Prompts.

    Converts complex decision matrices and research into a multi-shot
    video concept script formatted specifically for Google Veo video generation.
    """
    prompt = f"""You are the Google Veo Visual Synthesis Director.
Convert this research brief into a 3-Scene Cinematic Video Storyboard formatted for Google Veo video generation.

Research Topic: {research_title}
Synthesis Data:
{str(synthesis_data)[:3000]}

Generate a structured JSON response:
{{
  "video_title": "Title of the executive brief video",
  "veo_model": "veo-3.1-generate-preview",
  "aspect_ratio": "16:9",
  "scenes": [
    {{
      "scene_number": 1,
      "title": "The Problem Landscape",
      "visual_prompt": "Ultra-detailed visual description for Veo: Camera movement, lighting, cinematic atmosphere, 4K render...",
      "camera_motion": "Slow pan / Dolly zoom / Drone orbit",
      "voiceover_script": "Narrator voiceover text..."
    }},
    {{
      "scene_number": 2,
      "title": "Trade-off & Option Comparison",
      "visual_prompt": "Holographic data comparison grid, sleek modern tech aesthetic, studio lighting...",
      "camera_motion": "Smooth tracking shot",
      "voiceover_script": "Narrator voiceover text..."
    }},
    {{
      "scene_number": 3,
      "title": "Strategic Recommendation",
      "visual_prompt": "Inspiring forward-looking visualization, vibrant volumetric lighting, depth of field...",
      "camera_motion": "Crane up into wide view",
      "voiceover_script": "Narrator voiceover text..."
    }}
  ],
  "lyria_audio_cue": "Ambient modern synth soundscape with subtle pulse, 110 BPM, tech optimism",
  "veo_master_prompt": "Direct master prompt to paste into Google Veo video generator"
}}
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.4,
                response_mime_type="application/json",
                max_output_tokens=2000,
            ),
        )
        if response and response.text:
            import json
            import re
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
    except Exception as exc:
        logger.error("Veo storyboard generation failed: %s", str(exc))

    return {
        "video_title": f"Executive Visual Brief: {research_title}",
        "veo_model": "veo-3.1-generate-preview",
        "scenes": [
            {
                "scene_number": 1,
                "title": "Overview",
                "visual_prompt": f"Cinematic 3D visualization representing {research_title}, glowing data nodes, 8k octane render.",
                "camera_motion": "Smooth orbital pan",
                "voiceover_script": f"An in-depth analysis of {research_title} reveals key competitive trade-offs."
            }
        ],
        "lyria_audio_cue": "Ambient DeepMind Lyria research focus soundscape",
        "veo_master_prompt": f"Cinematic visualization of {research_title}, clean futuristic technology aesthetic, 4k.",
    }
