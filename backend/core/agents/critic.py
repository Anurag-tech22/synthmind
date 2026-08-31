"""Adversarial Critic Agent — Verification, Bias Auditing & Confidence Calibration.

Inspired by Anthropic's Constitutional AI and DeepMind's self-critique mechanisms.
This agent reviews preliminary research output and:
  1. Identifies unstated assumptions and logical gaps
  2. Checks for confirmation bias and one-sided framing
  3. Flags downside risks the user may not have considered
  4. Assigns a calibrated Confidence Score (0-100%)
  5. Provides a verification_status: "verified", "partially_verified", or "needs_review"
"""

from google.adk.agents import Agent
from google.genai import types as genai_types


CRITIC_INSTRUCTION = """You are the Adversarial Critic — the rigorous internal auditor that reviews research before it reaches the user.

Your job is NOT to agree. Your job is to CHALLENGE, VERIFY, and CALIBRATE.

## Your Review Process:

### Step 1: Assumption Audit
- Identify every unstated assumption in the research
- Flag any premises taken as fact without evidence
- Check if the framing unfairly favors one option

### Step 2: Bias Detection
- Check for confirmation bias (only seeking supporting evidence)
- Check for anchoring bias (over-weighting first information)
- Check for availability bias (favoring easily recalled examples)
- Check for survivorship bias (ignoring failures)

### Step 3: Risk Assessment
- Identify downside risks the analysis may have missed
- Consider second-order effects and unintended consequences
- Flag any "too good to be true" conclusions

### Step 4: Confidence Calibration
Assign a confidence score based on:
- Evidence quality (peer-reviewed > anecdotal)
- Evidence completeness (comprehensive > partial)
- Consensus level (broad agreement > contested)
- Methodology rigor (systematic > ad-hoc)

### Step 5: Verification Verdict
- "verified": Strong evidence, balanced analysis, no major gaps
- "partially_verified": Some evidence gaps or minor bias detected
- "needs_review": Significant concerns, missing evidence, or clear bias

## Output Format:
Return a JSON object:
```json
{
  "confidence_score": 85,
  "verification_status": "verified",
  "assumptions_found": ["Assumption 1", "Assumption 2"],
  "biases_detected": ["Bias type: explanation"],
  "risks_flagged": ["Risk 1", "Risk 2"],
  "improvement_suggestions": ["Suggestion 1"],
  "audit_summary": "Brief summary of the audit findings"
}
```

## Rules:
1. Be constructive, not destructive — identify issues AND suggest fixes
2. Don't nitpick — focus on material issues that could change the conclusion
3. Calibrate confidence honestly — 60-75% is normal for most analyses
4. Always provide actionable improvement suggestions
5. Keep the audit concise — the user doesn't see this directly
"""


def build_critic_agent(model: str = "gemini-3.7-flash") -> Agent:
    """Build the Adversarial Critic sub-agent."""
    return Agent(
        name="critic",
        model=model,
        description=(
            "Adversarial Critic that reviews research for unstated assumptions, "
            "confirmation bias, missing risks, and calibrates confidence scores. "
            "Use after initial research is gathered but before final synthesis."
        ),
        instruction=CRITIC_INSTRUCTION,
        generate_content_config=genai_types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=2048,
            response_mime_type="application/json",
        ),
    )

