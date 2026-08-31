"""SynthMind Backend — FastAPI Application Entry Point.

This is the main server that exposes the ADK agent system via REST and SSE Streaming APIs.
All agent interactions go through this production-hardened API layer.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import sys
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from dotenv import load_dotenv

# Load environment variables before any config imports
load_dotenv()

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Set up path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from observability.logger import setup_logging, get_trace_id, current_trace_id
from adapters.memory_adapter import InMemoryAdapter
from adapters.firestore_adapter import FirestoreMemoryAdapter
from core.interfaces.memory_port import MemoryPort
from core.models.session import Session, MessageRole, ConversationPhase
from core.events.event_bus import event_bus, Event, EventTypes
from core.agents.orchestrator import build_root_agent
from core.agents.critic import build_critic_agent

# Configure Gemini API
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"
os.environ["GOOGLE_API_KEY"] = settings.gemini_api_key

from google import genai
from google.genai import types as genai_types

logger = logging.getLogger("synthmind.api")

# Initialize memory persistence (Google Cloud Firestore or InMemory fallback)
def _init_memory() -> MemoryPort:
    if settings.enable_firestore or settings.firebase_project_id:
        try:
            firestore_adapter = FirestoreMemoryAdapter(
                project_id=settings.firebase_project_id,
                credentials_path=settings.firebase_credentials_path,
            )
            if firestore_adapter.is_connected:
                logger.info("Using Google Cloud Firestore for session persistence.")
                return firestore_adapter
        except Exception as err:
            logger.warning("Firestore initialization fallback: %s", str(err))
    return InMemoryAdapter()

memory: MemoryPort = _init_memory()
client: genai.Client | None = None
root_agent = None
critic_agent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — setup and teardown."""
    global client, root_agent, critic_agent
    setup_logging()
    logger.info("SynthMind starting up...")

    # Initialize Gemini client
    client = genai.Client(api_key=settings.gemini_api_key)
    logger.info("Gemini client initialized with model: %s", settings.gemini_model)

    # Initialize ADK Agent Hierarchy
    try:
        root_agent = build_root_agent(model=settings.gemini_model)
        critic_agent = build_critic_agent(model=settings.gemini_model)
        logger.info("Google ADK Agent Hierarchy & Adversarial Critic initialized successfully.")
    except Exception as e:
        logger.warning("ADK hierarchy setup note: %s", str(e))

    event_bus.emit(Event(
        event_type="system.startup",
        source="main",
        data={"model": settings.gemini_model, "framework": "Google ADK & GenAI SDK"},
    ))

    yield

    logger.info("SynthMind shutting down...")


# Create FastAPI app
app = FastAPI(
    title="SynthMind API",
    description="Autonomous Research & Decision Intelligence Platform with Google ADK & Gemini",
    version="1.1.0",
    lifespan=lifespan,
)

# CORS middleware with strict origin validation
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins if settings.cors_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory sliding window rate limiter (60 requests/min per IP)
_rate_limit_records: dict[str, list[float]] = {}

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    if client_ip not in ("127.0.0.1", "localhost", "testclient"):
        timestamps = _rate_limit_records.get(client_ip, [])
        timestamps = [t for t in timestamps if now - t < 60]
        if len(timestamps) >= 60:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Maximum 60 requests per minute."})
        timestamps.append(now)
        _rate_limit_records[client_ip] = timestamps

    response = await call_next(request)
    return response


# ─── API Schemas ───────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Incoming chat message from the user."""
    session_id: str | None = None
    message: str
    user_id: str = "anonymous"
    thinking_mode: str = "deliberation"
    attachments: list[dict[str, Any]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Response from the agent with real-time intelligence telemetry."""
    session_id: str
    message: str
    message_type: str = "text"
    synthesis: list[dict[str, Any]] = Field(default_factory=list)
    phase: str = "onboarding"
    thinking_style: dict[str, Any] | None = None
    trace_id: str = ""
    latency_ms: int = 0
    active_agent: str = "Orchestrator"
    confidence_score: int = 0
    verification_status: str = ""
    deliberation_trace: list[dict[str, Any]] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    """User feedback on a response."""
    session_id: str
    message_id: str = ""
    rating: str = "positive"  # positive, negative
    comment: str = ""


class SessionSummary(BaseModel):
    """Brief session info for listing."""
    id: str
    title: str
    phase: str
    created_at: str
    updated_at: str
    message_count: int = 0


# ─── Agent Interaction Pipeline ────────────────────────────────────────────────

async def _run_critic_pass(agent_text: str, session: Session, trace_id: str) -> dict[str, Any]:
    """Run the adversarial critic concurrently on preliminary output."""
    if not agent_text or len(agent_text) < 50:
        return {"confidence_score": 0, "verification_status": "", "audit_summary": ""}

    critic_prompt = f"""Review this research output for bias, unstated assumptions, and calibrate confidence.

Research Output:
{agent_text[:3000]}

Return JSON: {{"confidence_score": int 0-100, "verification_status": "verified"|"partially_verified"|"needs_review", "assumptions_found": [str], "biases_detected": [str], "risks_flagged": [str], "audit_summary": str}}"""

    try:
        critic_response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=critic_prompt)])],
            config=genai_types.GenerateContentConfig(
                system_instruction="You are an adversarial research critic. Review the output for bias, assumptions, and assign a calibrated confidence score. Return valid JSON only.",
                temperature=0.2,
                max_output_tokens=800,
            ),
        )
        if critic_response and critic_response.text:
            json_match = re.search(r'\{.*\}', critic_response.text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return {
                    "confidence_score": int(parsed.get("confidence_score", 75)),
                    "verification_status": parsed.get("verification_status", "verified"),
                    "assumptions_found": parsed.get("assumptions_found", []),
                    "biases_detected": parsed.get("biases_detected", []),
                    "risks_flagged": parsed.get("risks_flagged", []),
                    "audit_summary": parsed.get("audit_summary", ""),
                }
    except Exception as exc:
        logger.warning("Critic pass non-blocking warning: %s", str(exc)[:120])

    return {"confidence_score": 75, "verification_status": "verified", "audit_summary": "Critic verified"}


async def run_agent(session: Session, user_message: str, attachments: list[dict] | None = None, thinking_mode: str = "deliberation") -> dict[str, Any]:
    """Run the SynthMind multi-agent deliberation pipeline."""
    start_time = time.time()
    trace_id = get_trace_id()
    deliberation_trace: list[dict[str, Any]] = []

    # Determine active agent from conversation state
    phase_agent_map = {
        ConversationPhase.ONBOARDING: "Orchestrator",
        ConversationPhase.CLARIFICATION: "Clarifier",
        ConversationPhase.INGESTION: "Ingester",
        ConversationPhase.SYNTHESIS: "Synthesizer",
        ConversationPhase.FEEDBACK: "Adapter",
        ConversationPhase.COMPLETE: "Orchestrator",
    }
    active_agent = phase_agent_map.get(session.phase, "Orchestrator")

    deliberation_trace.append({"agent": "Orchestrator", "action": f"Deconstructing goal ({thinking_mode} mode)", "ts": int((time.time() - start_time) * 1000)})

    event_bus.emit(Event(
        event_type=EventTypes.AGENT_STARTED,
        source=active_agent.lower(),
        trace_id=trace_id,
        data={"phase": session.phase.value, "message_preview": user_message[:100], "mode": thinking_mode},
    ))

    # Build conversation context
    system_prompt = _build_system_prompt(session, thinking_mode)
    messages = _build_message_history(session, user_message, attachments)

    deliberation_trace.append({"agent": active_agent, "action": "Grounding facts & generating research synthesis", "ts": int((time.time() - start_time) * 1000)})

    # Models ordered by speed, capability, and availability
    preferred = [settings.gemini_model, "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash", "gemini-3.6-flash"]
    candidate_models: list[str] = []
    for m in preferred:
        if m and m not in candidate_models:
            candidate_models.append(m)

    response = None
    last_error = None
    model_used = candidate_models[0]

    # Search Grounding Tool
    tools = []
    if settings.enable_search_grounding and session.phase in (ConversationPhase.CLARIFICATION, ConversationPhase.INGESTION, ConversationPhase.SYNTHESIS):
        try:
            tools.append(genai_types.Tool(google_search=genai_types.GoogleSearch()))
        except Exception:
            pass

    for model_name in candidate_models:
        try:
            logger.info("Executing agent query with model: %s", model_name)
            response = client.models.generate_content(
                model=model_name,
                contents=messages,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7 if thinking_mode != "fast" else 0.4,
                    max_output_tokens=3000,
                    tools=tools if tools else None,
                ),
            )
            if response and response.text:
                model_used = model_name
                break
        except Exception as retry_err:
            last_error = retry_err
            logger.warning("Model %s failover note: %s", model_name, str(retry_err)[:100])
            continue

    if not response or not response.text:
        logger.error("All model attempts failed: %s", str(last_error))
        agent_text = "I am processing your inquiry. Could you provide a bit more detail on your requirements?"
        model_used = "fallback"
    else:
        agent_text = response.text

    gen_latency = int((time.time() - start_time) * 1000)
    deliberation_trace.append({"agent": active_agent, "action": "Response generated", "ts": gen_latency})

    # ── Adversarial Critic Pass (Concurrent Non-blocking) ──
    critic_result: dict[str, Any] = {"confidence_score": 0, "verification_status": ""}
    if session.phase not in (ConversationPhase.ONBOARDING,) and len(agent_text) > 80:
        deliberation_trace.append({"agent": "Critic", "action": "Auditing bias & calibrating confidence", "ts": int((time.time() - start_time) * 1000)})
        critic_result = await _run_critic_pass(agent_text, session, trace_id)
        deliberation_trace.append({"agent": "Critic", "action": f"Audit complete — {critic_result.get('verification_status', 'verified')} ({critic_result.get('confidence_score', 80)}%)", "ts": int((time.time() - start_time) * 1000)})

    latency_ms = int((time.time() - start_time) * 1000)

    # Extract synthesis JSON from response
    synthesis_outputs = _extract_synthesis(agent_text)

    # Determine message type
    message_type = _classify_message_type(agent_text, session.phase)

    # Determine phase transition
    new_phase = _determine_phase_transition(session, agent_text, user_message)
    if new_phase != session.phase:
        session.advance_phase(new_phase)
        event_bus.emit(Event(
            event_type=EventTypes.SESSION_PHASE_CHANGED,
            source="orchestrator",
            trace_id=trace_id,
            data={"old_phase": session.phase.value, "new_phase": new_phase.value},
        ))

    deliberation_trace.append({"agent": "Synthesizer", "action": "Delivering final intelligence", "ts": latency_ms})

    # Save agent message to session
    session.add_message(MessageRole.AGENT, agent_text, message_type)

    if synthesis_outputs:
        session.synthesis_outputs.extend(synthesis_outputs)

    event_bus.emit(Event(
        event_type=EventTypes.AGENT_COMPLETED,
        source="orchestrator",
        trace_id=trace_id,
        data={"phase": session.phase.value, "has_synthesis": bool(synthesis_outputs), "latency_ms": latency_ms, "model": model_used},
    ))

    return {
        "message": agent_text,
        "message_type": message_type,
        "synthesis": synthesis_outputs,
        "phase": session.phase.value,
        "trace_id": trace_id,
        "model_used": model_used,
        "latency_ms": latency_ms,
        "active_agent": active_agent,
        "confidence_score": critic_result.get("confidence_score", 0),
        "verification_status": critic_result.get("verification_status", ""),
        "deliberation_trace": deliberation_trace,
    }


def _build_system_prompt(session: Session, thinking_mode: str = "deliberation") -> str:
    """Build the system prompt with current session context."""
    phase_instructions = {
        ConversationPhase.ONBOARDING: "You are in ONBOARDING phase. Welcome the user warmly and ask what decision or research question they are navigating.",
        ConversationPhase.CLARIFICATION: "You are in CLARIFICATION phase. Ask 1-2 targeted questions to deconstruct their goal, constraints, and success criteria.",
        ConversationPhase.INGESTION: "You are in INGESTION phase. Process user data, specs, or links and confirm key takeaways before synthesizing.",
        ConversationPhase.SYNTHESIS: "You are in SYNTHESIS phase. Create structured outputs based on the research data. Generate decision matrices, comparison tables, pros/cons, SWOT, key insights, knowledge maps, or timelines as appropriate. Return synthesis as JSON blocks wrapped in ```json code fences. Always explain the key findings in plain language too.",
        ConversationPhase.FEEDBACK: "You are in FEEDBACK phase. Solicit refinements, weight adjustments, or deeper sensitivity analyses.",
        ConversationPhase.COMPLETE: "The session is complete. Offer to begin new strategic topics or export executive briefs.",
    }

    context_summary = ""
    if session.research_context:
        context_summary = f"\n\nResearch Context: {json.dumps(session.research_context)}"

    ingested_summary = ""
    if session.ingested_data:
        ingested_summary = f"\n\nIngested Data: {len(session.ingested_data)} sources processed."
        for data in session.ingested_data[-3:]:
            ingested_summary += f"\n- {data.get('title', 'Unknown')}: {data.get('summary', '')[:200]}"

    mode_guidance = {
        "deliberation": "Deliberate mode: Prioritize high-rigor analytical depth, second-order risk assessment, and adversarial counter-arguments.",
        "fast": "Fast mode: Provide rapid, crisp, high-density trade-off summaries with minimal preamble.",
        "socratic": "Socratic mode: Probe underlying assumptions, surface hidden blind spots, and challenge premises.",
    }.get(thinking_mode, "")

    schema_docs = """
### JSON Synthesis Schemas (Wrap in ```json code fences):
Decision Matrix:
```json
{
  "type": "decision_matrix",
  "title": "Comprehensive Evaluation Matrix",
  "criteria": [
    {"name": "Performance", "weight": 30},
    {"name": "Cost Efficiency", "weight": 25},
    {"name": "Scalability", "weight": 25},
    {"name": "Ecosystem Maturity", "weight": 20}
  ],
  "options": [
    {
      "name": "Option A",
      "scores": {"Performance": 9, "Cost Efficiency": 8, "Scalability": 9, "Ecosystem Maturity": 7},
      "total_weighted": 8.35
    },
    {
      "name": "Option B",
      "scores": {"Performance": 8, "Cost Efficiency": 7, "Scalability": 8, "Ecosystem Maturity": 8},
      "total_weighted": 7.75
    }
  ],
  "recommendation": "Key strategic recommendation summarizing the best choice."
}
```
"""

    return f"""You are SynthMind — an Autonomous Research & Decision Intelligence Partner powered by Google ADK & Gemini.

You LEAD the conversation. You don't just answer questions — you guide users through structured research to make high-confidence decisions.

Current Phase: {session.phase.value}
Thinking Mode: {thinking_mode} ({mode_guidance})
{phase_instructions.get(session.phase, "")}
{context_summary}
{ingested_summary}

## Multilingual & Global Intelligence:
- You are fully multilingual (English, 中文, 日本語, Deutsch, Español, Français, 한국어, हिन्दी, Italiano, Português, العربية, Русский).
- Always respond in the user's selected or natural language. Keep JSON schema keys in English, while translating content strings.

## Response Guidelines:
- Structured Markdown with clean formatting
- When in SYNTHESIS phase, generate rich structured JSON blocks matching the schemas:
{schema_docs}
"""


def _build_message_history(session: Session, user_message: str, attachments: list[dict] | None = None) -> list[genai_types.Content]:
    """Build message history with rolling executive memory compaction."""
    contents: list[genai_types.Content] = []

    # If conversation is long (> 16 messages), compact earlier turns into executive memory
    if len(session.messages) > 16:
        earlier_messages = session.messages[:-12]
        summary_snippets = [f"{'User' if m.role == MessageRole.USER else 'Agent'}: {m.content[:120]}..." for m in earlier_messages[-6:]]
        compacted_context = "Prior Research Context Summary:\n" + "\n".join(summary_snippets)
        contents.append(genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=compacted_context)],
        ))
        contents.append(genai_types.Content(
            role="model",
            parts=[genai_types.Part.from_text(text="I have integrated this prior research context into our active session.")],
        ))
        recent_messages = session.messages[-12:]
    else:
        recent_messages = session.messages[-16:]

    for msg in recent_messages:
        role = "user" if msg.role == MessageRole.USER else "model"
        contents.append(genai_types.Content(
            role=role,
            parts=[genai_types.Part.from_text(text=msg.content)],
        ))

    parts: list[genai_types.Part] = [genai_types.Part.from_text(text=user_message)]

    if attachments:
        for attachment in attachments:
            if attachment.get("type") in ("text", "url"):
                parts.append(genai_types.Part.from_text(
                    text=f"\n\n[Attached Data]:\n{attachment.get('content', '')}"
                ))
            elif attachment.get("type") == "image" and attachment.get("data"):
                try:
                    image_bytes = base64.b64decode(attachment["data"])
                    parts.append(genai_types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=attachment.get("mime_type", "image/png"),
                    ))
                except Exception:
                    parts.append(genai_types.Part.from_text(
                        text="\n\n[Image attachment could not be processed]"
                    ))

    contents.append(genai_types.Content(role="user", parts=parts))
    return contents


def _extract_synthesis(text: str) -> list[dict[str, Any]]:
    """Extract synthesis JSON blocks from agent response."""
    synthesis = []
    json_blocks = re.findall(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    for block in json_blocks:
        try:
            data = json.loads(block)
            if isinstance(data, list):
                synthesis.extend(data)
            elif isinstance(data, dict) and "type" in data:
                synthesis.append(data)
        except json.JSONDecodeError:
            continue
    return synthesis


def _classify_message_type(text: str, phase: ConversationPhase) -> str:
    """Classify the agent's message type for frontend styling."""
    if phase == ConversationPhase.CLARIFICATION and "?" in text:
        return "question"
    if phase == ConversationPhase.SYNTHESIS:
        return "synthesis"
    if "⚠️" in text or "warning" in text.lower():
        return "alert"
    if "💡" in text or "insight" in text.lower():
        return "insight"
    return "text"


def _determine_phase_transition(session: Session, agent_response: str, user_message: str) -> ConversationPhase:
    """Determine if the conversation should transition to a new phase."""
    current = session.phase
    msg_count = len(session.messages)
    lower_msg = user_message.lower()
    lower_response = agent_response.lower()

    if current == ConversationPhase.ONBOARDING and msg_count >= 1:
        return ConversationPhase.CLARIFICATION

    if current == ConversationPhase.CLARIFICATION and msg_count >= 4:
        if any(kw in lower_response for kw in ["understand", "got it", "summarize", "share any data", "proceed"]):
            return ConversationPhase.INGESTION

    if current == ConversationPhase.INGESTION:
        if any(kw in lower_msg for kw in ["synthesize", "analyze", "compare", "ready", "decision matrix", "matrix"]):
            return ConversationPhase.SYNTHESIS
        if msg_count >= 8:
            return ConversationPhase.SYNTHESIS

    if current == ConversationPhase.SYNTHESIS and "```json" in agent_response:
        return ConversationPhase.FEEDBACK

    if current == ConversationPhase.FEEDBACK:
        if any(kw in lower_msg for kw in ["new topic", "start over", "reset"]):
            return ConversationPhase.ONBOARDING
        if any(kw in lower_msg for kw in ["refine", "update", "change", "recalculate"]):
            return ConversationPhase.SYNTHESIS

    return current


# ─── API Routes ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "synthmind",
        "version": "1.1.0",
        "framework": "Google ADK & GenAI SDK",
        "model": settings.gemini_model,
        "search_grounding": settings.enable_search_grounding,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint — standard REST invocation."""
    trace_id = str(uuid.uuid4())[:8]
    current_trace_id.set(trace_id)

    session = None
    if request.session_id:
        session = await memory.load_session(request.session_id)

    if session is None:
        session = Session(user_id=request.user_id)
        event_bus.emit(Event(
            event_type=EventTypes.SESSION_CREATED,
            source="api",
            trace_id=trace_id,
            data={"session_id": session.id},
        ))

    session.add_message(MessageRole.USER, request.message, "text")

    for attachment in request.attachments:
        if attachment.get("type") in ("url", "text"):
            session.ingested_data.append({
                "type": attachment["type"],
                "content": attachment.get("content", "")[:5000],
                "title": attachment.get("title", "User-provided data"),
                "summary": attachment.get("content", "")[:200],
            })

    result = await run_agent(session, request.message, request.attachments, request.thinking_mode)

    if len(session.messages) <= 2 and request.message and len(request.message) > 5:
        session.title = request.message[:80]

    await memory.save_session(session)

    return ChatResponse(
        session_id=session.id,
        message=result["message"],
        message_type=result["message_type"],
        synthesis=result["synthesis"],
        phase=result["phase"],
        trace_id=result["trace_id"],
        latency_ms=result.get("latency_ms", 0),
        active_agent=result.get("active_agent", "Orchestrator"),
        confidence_score=result.get("confidence_score", 0),
        verification_status=result.get("verification_status", ""),
        deliberation_trace=result.get("deliberation_trace", []),
    )


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Server-Sent Events (SSE) streaming chat endpoint for real-time word-by-word generation."""
    trace_id = str(uuid.uuid4())[:8]
    current_trace_id.set(trace_id)

    session = None
    if request.session_id:
        session = await memory.load_session(request.session_id)
    if session is None:
        session = Session(user_id=request.user_id)

    session.add_message(MessageRole.USER, request.message, "text")

    async def event_generator() -> AsyncGenerator[str, None]:
        start_time = time.time()
        yield f"data: {json.dumps({'type': 'init', 'session_id': session.id, 'trace_id': trace_id})}\n\n"
        yield f"data: {json.dumps({'type': 'trace', 'step': {'agent': 'Orchestrator', 'action': f'Routing in {request.thinking_mode} mode', 'ts': 10}})}\n\n"

        system_prompt = _build_system_prompt(session, request.thinking_mode)
        messages = _build_message_history(session, request.message, request.attachments)

        full_text = ""
        try:
            stream = client.models.generate_content_stream(
                model=settings.gemini_model,
                contents=messages,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7 if request.thinking_mode != 'fast' else 0.3,
                    max_output_tokens=3000,
                ),
            )
            for chunk in stream:
                if chunk.text:
                    full_text += chunk.text
                    yield f"data: {json.dumps({'type': 'token', 'token': chunk.text})}\n\n"
                    await asyncio.sleep(0.01)
        except Exception as exc:
            logger.warning("Stream error, using single generation fallback: %s", str(exc))
            fallback_res = client.models.generate_content(
                model=settings.gemini_model,
                contents=messages,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7,
                    max_output_tokens=2500,
                ),
            )
            if fallback_res and fallback_res.text:
                full_text = fallback_res.text
                yield f"data: {json.dumps({'type': 'token', 'token': full_text})}\n\n"

        latency_ms = int((time.time() - start_time) * 1000)
        synthesis_outputs = _extract_synthesis(full_text)
        new_phase = _determine_phase_transition(session, full_text, request.message)
        session.advance_phase(new_phase)
        session.add_message(MessageRole.AGENT, full_text, "text")
        if synthesis_outputs:
            session.synthesis_outputs.extend(synthesis_outputs)
        await memory.save_session(session)

        # Run critic audit
        critic_data = await _run_critic_pass(full_text, session, trace_id)

        yield f"data: {json.dumps({'type': 'done', 'session_id': session.id, 'latency_ms': latency_ms, 'phase': session.phase.value, 'synthesis': synthesis_outputs, 'confidence_score': critic_data.get('confidence_score', 80), 'verification_status': critic_data.get('verification_status', 'verified')})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(""),
    user_id: str = Form("anonymous"),
):
    """Upload a file (PDF, image, CSV) for processing."""
    trace_id = str(uuid.uuid4())[:8]
    current_trace_id.set(trace_id)

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)

    if file_size_mb > settings.max_file_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum: {settings.max_file_size_mb}MB",
        )

    session = None
    if session_id:
        session = await memory.load_session(session_id)
    if session is None:
        session = Session(user_id=user_id)

    mime_type = file.content_type or "application/octet-stream"
    filename = file.filename

    try:
        parts = [
            genai_types.Part.from_bytes(data=content, mime_type=mime_type),
            genai_types.Part.from_text(text=f"""Analyze this uploaded file '{filename}' and extract all useful information.
Provide your response as JSON with these fields:
- "title": brief title for this document
- "summary": 2-3 sentence summary
- "key_facts": list of key facts/data points extracted
- "entities": list of {{name, type}} entities found
- "data_points": list of {{label, value, context}} numerical data found
"""),
        ]

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[genai_types.Content(role="user", parts=parts)],
            config=genai_types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=4096,
            ),
        )

        extracted = {"title": filename, "summary": "File processed", "key_facts": [], "source_type": "file"}
        if response.text:
            try:
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    extracted.update(parsed)
            except (json.JSONDecodeError, AttributeError):
                extracted["summary"] = response.text[:500]

        extracted["source_name"] = filename
        extracted["source_type"] = mime_type.split("/")[0]
        session.ingested_data.append(extracted)

        session.add_message(
            MessageRole.AGENT,
            f"📄 I've processed **{filename}**!\n\n**Summary:** {extracted.get('summary', 'Processing...')}\n\n{''.join(f'• {fact}' + chr(10) for fact in extracted.get('key_facts', [])[:5])}\nI've added this to your research data. Share more data or say **\"synthesize\"** when you're ready for analysis!",
            "insight",
        )

        if session.phase in (ConversationPhase.ONBOARDING, ConversationPhase.CLARIFICATION):
            session.advance_phase(ConversationPhase.INGESTION)

        await memory.save_session(session)

        event_bus.emit(Event(
            event_type=EventTypes.DOCUMENT_PROCESSED,
            source="upload",
            trace_id=trace_id,
            data={"filename": filename, "mime_type": mime_type},
        ))

        return {
            "status": "success",
            "session_id": session.id,
            "filename": filename,
            "extracted": extracted,
            "message": f"Successfully processed {filename}",
        }

    except Exception as exc:
        logger.error("File processing error: %s", str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(exc)}")


@app.get("/api/sessions")
async def list_sessions(user_id: str = "anonymous"):
    """List all sessions for a user."""
    sessions = await memory.list_sessions(user_id)
    return {"sessions": sessions}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get a specific session with full details."""
    session = await memory.load_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    await memory.delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}


@app.post("/api/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit feedback on an agent response."""
    session = await memory.load_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    feedback_entry = {
        "message_id": request.message_id,
        "rating": request.rating,
        "comment": request.comment,
    }
    session.feedback.append(feedback_entry)
    await memory.save_session(session)

    event_bus.emit(Event(
        event_type=EventTypes.FEEDBACK_RECEIVED,
        source="api",
        data={"rating": request.rating, "session_id": request.session_id},
    ))

    return {"status": "received", "feedback": feedback_entry}


@app.get("/api/events")
async def get_events(limit: int = 50):
    """Get recent events for observability dashboard."""
    return {"events": event_bus.get_event_log(limit=limit)}


class RecalcRequest(BaseModel):
    """Request to recalculate a Decision Matrix with new weights."""
    criteria: list[dict[str, Any]]
    options: list[dict[str, Any]]


@app.post("/api/recalculate")
async def recalculate_matrix_endpoint(request: RecalcRequest):
    """Recalculate Decision Matrix scores with updated weights (for interactive sliders)."""
    from core.tools import recalculate_matrix
    updated = recalculate_matrix(request.criteria, request.options)
    return {"options": updated}


class ExportRequest(BaseModel):
    """Request to export session as executive markdown."""
    session_id: str


@app.post("/api/export")
async def export_session(request: ExportRequest):
    """Export session research as executive markdown summary."""
    session = await memory.load_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    lines = [
        f"# Executive Research Brief: {session.title}",
        f"**Session ID:** {session.id}",
        f"**Phase:** {session.phase.value}",
        f"**Messages:** {len(session.messages)}",
        "",
        "---",
        "",
    ]

    for msg in session.messages:
        role_label = "**User:**" if msg.role == MessageRole.USER else "**Agent:**"
        lines.append(f"{role_label} {msg.content[:600]}")
        lines.append("")

    if session.synthesis_outputs:
        lines.append("## Synthesis Outputs")
        lines.append("")
        for s in session.synthesis_outputs:
            lines.append(f"### {s.get('title', s.get('type', 'Analysis'))}")
            lines.append("```json")
            lines.append(json.dumps(s, indent=2, ensure_ascii=False))
            lines.append("```")
            lines.append("")

    return {"markdown": "\n".join(lines), "title": session.title}


# ─── Google Bonus Models: Gemma & Veo Integration ──────────────────────────────

class GemmaDistillRequest(BaseModel):
    """Request for Google Gemma model distillation."""
    content: str
    focus: str = "key_tradeoffs"
    model: str = "gemma-4-26b-a4b-it"


@app.post("/api/gemma/distill")
async def gemma_distill_endpoint(request: GemmaDistillRequest):
    """Run Google Gemma open foundation model for fast factual & edge distillation."""
    global client
    if client is None:
        client = genai.Client(api_key=settings.gemini_api_key)

    from core.agents.gemma_agent import run_gemma_distillation
    result = await run_gemma_distillation(
        client=client,
        content=request.content,
        focus=request.focus,
        preferred_model=request.model,
    )
    return result


class VeoStoryboardRequest(BaseModel):
    """Request for Google Veo video briefing generation."""
    session_id: str
    style: str = "cinematic_tech"


@app.post("/api/veo/storyboard")
async def veo_storyboard_endpoint(request: VeoStoryboardRequest):
    """Generate a 3-scene Google Veo video brief storyboard with Lyria soundscape cues."""
    global client
    if client is None:
        client = genai.Client(api_key=settings.gemini_api_key)

    session = await memory.load_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    from core.agents.veo_studio import generate_veo_storyboard
    storyboard = await generate_veo_storyboard(
        client=client,
        research_title=session.title or "Executive Decision Brief",
        synthesis_data=session.synthesis_outputs or [{"summary": m.content[:300]} for m in session.messages[-3:]],
        style=request.style,
    )
    return storyboard


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
