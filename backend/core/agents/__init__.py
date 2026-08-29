"""SynthMind Agent System — Google ADK Multi-Agent Orchestration.

This package defines 5 specialized agents orchestrated through Google ADK:
- Orchestrator: Root agent that routes and manages workflow state
- Clarifier: Socratic questioning to understand user goals
- Ingester: Multimodal data processing (PDF, images, URLs, text)
- Synthesizer: Creates structured decision-support outputs
- Adapter: Learns and adapts to user's thinking style
"""

from core.agents.orchestrator import build_root_agent

__all__ = ["build_root_agent"]
