"""Synthesis output domain models — structured decision-support formats.

These models represent the 7 visual synthesis types that SynthMind generates
from raw research data. Each produces structured JSON for frontend rendering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DecisionMatrix:
    """Weighted scoring grid: criteria × options with scores.

    Example: Comparing 3 laptops across Price, Performance, Battery, Display.
    Each criterion has a weight (0-100) and each option gets a score (0-10).
    """
    title: str = ""
    criteria: list[dict[str, Any]] = field(default_factory=list)
    # Each criterion: {"name": str, "weight": int, "description": str}
    options: list[dict[str, Any]] = field(default_factory=list)
    # Each option: {"name": str, "scores": {"criterion_name": float}, "total": float}
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "decision_matrix",
            "title": self.title,
            "criteria": self.criteria,
            "options": self.options,
            "recommendation": self.recommendation,
        }


@dataclass
class ComparisonTable:
    """Side-by-side feature comparison with difference highlighting.

    Each feature is compared across all items, with a verdict on which is best.
    """
    title: str = ""
    items: list[str] = field(default_factory=list)  # Column headers
    features: list[dict[str, Any]] = field(default_factory=list)
    # Each feature: {"name": str, "values": {"item_name": str}, "winner": str}
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "comparison_table",
            "title": self.title,
            "items": self.items,
            "features": self.features,
            "summary": self.summary,
        }


@dataclass
class ProsCons:
    """Pros and cons analysis with confidence scores.

    Each pro/con has a text description and a confidence percentage.
    """
    title: str = ""
    subject: str = ""
    pros: list[dict[str, Any]] = field(default_factory=list)
    # Each: {"text": str, "confidence": int (0-100), "source": str}
    cons: list[dict[str, Any]] = field(default_factory=list)
    verdict: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "pros_cons",
            "title": self.title,
            "subject": self.subject,
            "pros": self.pros,
            "cons": self.cons,
            "verdict": self.verdict,
        }


@dataclass
class SwotAnalysis:
    """SWOT (Strengths, Weaknesses, Opportunities, Threats) analysis.

    Four-quadrant strategic analysis framework.
    """
    title: str = ""
    subject: str = ""
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    opportunities: list[str] = field(default_factory=list)
    threats: list[str] = field(default_factory=list)
    strategic_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "swot_analysis",
            "title": self.title,
            "subject": self.subject,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "opportunities": self.opportunities,
            "threats": self.threats,
            "strategic_summary": self.strategic_summary,
        }


@dataclass
class KeyInsight:
    """A single key insight extracted from research data."""
    text: str = ""
    importance: int = 5  # 1-10 scale
    category: str = ""  # finding, warning, recommendation, opportunity
    evidence: str = ""   # Source reference
    confidence: int = 80  # 0-100

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "key_insight",
            "text": self.text,
            "importance": self.importance,
            "category": self.category,
            "evidence": self.evidence,
            "confidence": self.confidence,
        }


@dataclass
class KnowledgeMap:
    """Force-directed concept graph showing relationships.

    Nodes are concepts, edges are relationships with labels.
    """
    title: str = ""
    nodes: list[dict[str, Any]] = field(default_factory=list)
    # Each node: {"id": str, "label": str, "group": str, "size": int}
    edges: list[dict[str, Any]] = field(default_factory=list)
    # Each edge: {"source": str, "target": str, "label": str, "weight": float}

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "knowledge_map",
            "title": self.title,
            "nodes": self.nodes,
            "edges": self.edges,
        }


@dataclass
class TimelineEntry:
    """A single entry in a timeline visualization."""
    date: str = ""
    title: str = ""
    description: str = ""
    category: str = ""  # milestone, event, deadline, decision
    importance: int = 5  # 1-10

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "timeline_entry",
            "date": self.date,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "importance": self.importance,
        }


@dataclass
class SynthesisOutput:
    """Container for all synthesis outputs from a research session."""
    session_id: str = ""
    decision_matrices: list[DecisionMatrix] = field(default_factory=list)
    comparison_tables: list[ComparisonTable] = field(default_factory=list)
    pros_cons: list[ProsCons] = field(default_factory=list)
    swot_analyses: list[SwotAnalysis] = field(default_factory=list)
    key_insights: list[KeyInsight] = field(default_factory=list)
    knowledge_maps: list[KnowledgeMap] = field(default_factory=list)
    timelines: list[list[TimelineEntry]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "decision_matrices": [m.to_dict() for m in self.decision_matrices],
            "comparison_tables": [t.to_dict() for t in self.comparison_tables],
            "pros_cons": [p.to_dict() for p in self.pros_cons],
            "swot_analyses": [s.to_dict() for s in self.swot_analyses],
            "key_insights": [i.to_dict() for i in self.key_insights],
            "knowledge_maps": [k.to_dict() for k in self.knowledge_maps],
            "timelines": [[e.to_dict() for e in t] for t in self.timelines],
        }

    def all_outputs(self) -> list[dict[str, Any]]:
        """Get all synthesis outputs as a flat list for the frontend."""
        outputs: list[dict[str, Any]] = []
        outputs.extend(m.to_dict() for m in self.decision_matrices)
        outputs.extend(t.to_dict() for t in self.comparison_tables)
        outputs.extend(p.to_dict() for p in self.pros_cons)
        outputs.extend(s.to_dict() for s in self.swot_analyses)
        outputs.extend(i.to_dict() for i in self.key_insights)
        outputs.extend(k.to_dict() for k in self.knowledge_maps)
        for timeline in self.timelines:
            outputs.append({
                "type": "timeline",
                "entries": [e.to_dict() for e in timeline],
            })
        return outputs
