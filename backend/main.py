"""SynthMind Backend — FastAPI Application Entry Point.

This is the main server that exposes the ADK agent system via REST API.
All agent interactions go through this API layer.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
import base64
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv

# Load environment variables before any config imports
load_dotenv()

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Set up path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from observability.logger import setup_logging, get_trace_id, current_trace_id
from adapters.memory_adapter import InMemoryAdapter
from core.models.session import Session, MessageRole, ConversationPhase
from core.events.event_bus import event_bus, Event, EventTypes

# Configure Gemini API
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"
os.environ["GOOGLE_API_KEY"] = settings.gemini_api_key

from google import genai
from google.genai import types as genai_types

logger = logging.getLogger("synthmind.api")

# Global state
memory = InMemoryAdapter()
client: genai.Client | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — setup and teardown."""
    global client
    setup_logging()
    logger.info("SynthMind starting up...")

    # Initialize Gemini client
    client = genai.Client(api_key=settings.gemini_api_key)
    logger.info("Gemini client initialized with model: %s", settings.gemini_model)

    event_bus.emit(Event(
        event_type="system.startup",
        source="main",
        data={"model": settings.gemini_model},
    ))

    yield

    logger.info("SynthMind shutting down...")


# Create FastAPI app
app = FastAPI(
    title="SynthMind API",
    description="Adaptive Research & Decision Intelligence Partner",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for hackathon demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── API Schemas ───────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Incoming chat message from the user."""
    session_id: str | None = None
    message: str
    user_id: str = "anonymous"
    attachments: list[dict[str, Any]] = []  # [{type: "url"|"text", content: str}]


class ChatResponse(BaseModel):
    """Response from the agent."""
    session_id: str
    message: str
    message_type: str = "text"
    synthesis: list[dict[str, Any]] = []
    phase: str = "onboarding"
    thinking_style: dict[str, Any] | None = None
    trace_id: str = ""


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


# ─── Agent Interaction ──────────────────────────────────────────────────────────

async def run_agent(session: Session, user_message: str, attachments: list[dict] | None = None) -> dict[str, Any]:
    """Run the SynthMind agent system on a user message.

    This is the core interaction loop. It:
    1. Builds context from session history
    2. Calls Gemini 3.7 Flash with the orchestrator system prompt
    3. Parses the response for synthesis outputs
    4. Returns the agent response with any structured outputs
    """
    trace_id = get_trace_id()

    event_bus.emit(Event(
        event_type=EventTypes.AGENT_STARTED,
        source="orchestrator",
        trace_id=trace_id,
        data={"phase": session.phase.value, "message_preview": user_message[:100]},
    ))

    # Build conversation context
    system_prompt = _build_system_prompt(session)
    messages = _build_message_history(session, user_message, attachments)

    try:
        # Call Gemini with retry + model fallback for 503 overload errors
        import asyncio
        models_to_try = [settings.gemini_model, "gemini-3.5-flash"]
        response = None
        last_error = None

        for model_name in models_to_try:
            for attempt in range(3):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=messages,
                        config=genai_types.GenerateContentConfig(
                            system_instruction=system_prompt,
                            temperature=0.7,
                            max_output_tokens=4096,
                        ),
                    )
                    if response and response.text:
                        break
                except Exception as retry_err:
                    last_error = retry_err
                    if "503" in str(retry_err) or "UNAVAILABLE" in str(retry_err):
                        wait_time = (2 ** attempt) * 2  # 2, 4, 8 seconds
                        logger.warning("Model %s attempt %d failed (503), retrying in %ds...", model_name, attempt + 1, wait_time)
                        await asyncio.sleep(wait_time)
                    else:
                        raise
            if response and response.text:
                break
            logger.warning("All retries exhausted for %s, trying fallback model...", model_name)

        if not response or not response.text:
            raise last_error or Exception("All model attempts failed")

        agent_text = response.text

        # Try to extract synthesis JSON from response
        synthesis_outputs = _extract_synthesis(agent_text)

        # Determine message type
        message_type = _classify_message_type(agent_text, session.phase)

        # Determine if we should advance the phase
        new_phase = _determine_phase_transition(session, agent_text, user_message)
        if new_phase != session.phase:
            session.advance_phase(new_phase)
            event_bus.emit(Event(
                event_type=EventTypes.SESSION_PHASE_CHANGED,
                source="orchestrator",
                trace_id=trace_id,
                data={"old_phase": session.phase.value, "new_phase": new_phase.value},
            ))

        # Save agent message to session
        session.add_message(MessageRole.AGENT, agent_text, message_type)

        # Store synthesis outputs if any
        if synthesis_outputs:
            session.synthesis_outputs.extend(synthesis_outputs)

        event_bus.emit(Event(
            event_type=EventTypes.AGENT_COMPLETED,
            source="orchestrator",
            trace_id=trace_id,
            data={"phase": session.phase.value, "has_synthesis": bool(synthesis_outputs)},
        ))

        return {
            "message": agent_text,
            "message_type": message_type,
            "synthesis": synthesis_outputs,
            "phase": session.phase.value,
            "trace_id": trace_id,
        }

    except Exception as exc:
        logger.error("Agent error: %s", str(exc), exc_info=True)
        event_bus.emit(Event(
            event_type=EventTypes.AGENT_ERROR,
            source="orchestrator",
            trace_id=trace_id,
            data={"error": str(exc)},
        ))
        return {
            "message": f"I encountered an issue, but I'm still here! Let me try a different approach. Could you rephrase your request?\n\n*Technical detail: {str(exc)[:200]}*",
            "message_type": "alert",
            "synthesis": [],
            "phase": session.phase.value,
            "trace_id": trace_id,
        }


def _build_system_prompt(session: Session) -> str:
    """Build the system prompt with current session context."""
    phase_instructions = {
        ConversationPhase.ONBOARDING: "You are in ONBOARDING phase. Welcome the user warmly and ask what they're trying to figure out. Offer templates: Compare options, Research a topic, Make a decision, or Learn something new.",
        ConversationPhase.CLARIFICATION: "You are in CLARIFICATION phase. Ask 1-2 targeted questions to understand their goal, constraints, and preferences. Be specific. After enough context, summarize your understanding.",
        ConversationPhase.INGESTION: "You are in INGESTION phase. The user may share data (text, URLs, documents). Process and acknowledge each piece. Ask if they have more data or if you should start synthesizing.",
        ConversationPhase.SYNTHESIS: "You are in SYNTHESIS phase. Create structured outputs based on the research data. Generate decision matrices, comparison tables, pros/cons, SWOT, key insights, knowledge maps, or timelines as appropriate. Return synthesis as JSON blocks wrapped in ```json code fences. Always explain the key findings in plain language too.",
        ConversationPhase.FEEDBACK: "You are in FEEDBACK phase. Ask how useful the synthesis was. What would they change? Capture their feedback to improve.",
        ConversationPhase.COMPLETE: "The session is complete. Offer to start a new research topic or refine the current analysis.",
    }

    context_summary = ""
    if session.research_context:
        context_summary = f"\n\nResearch Context: {json.dumps(session.research_context)}"

    ingested_summary = ""
    if session.ingested_data:
        ingested_summary = f"\n\nIngested Data: {len(session.ingested_data)} sources processed."
        for data in session.ingested_data[-3:]:  # Last 3 sources
            ingested_summary += f"\n- {data.get('title', 'Unknown')}: {data.get('summary', '')[:200]}"

    return f"""You are SynthMind — an Adaptive Research & Decision Intelligence Partner.

You LEAD the conversation. You don't just answer questions — you guide users through structured research to make better decisions.

Current Phase: {session.phase.value}
{phase_instructions.get(session.phase, "")}
{context_summary}
{ingested_summary}

## Response Guidelines:
- Be warm, confident, and proactive
- Keep responses focused and actionable
- Use markdown formatting for readability
- When in SYNTHESIS phase, include structured JSON outputs in ```json blocks
- Always tell the user what's coming next
- Reference their actual data and goals specifically

## Synthesis Output Format (use in SYNTHESIS phase):
When creating synthesis, wrap each output in a ```json code fence with a "type" field:
- "decision_matrix" — weighted scoring grid
- "comparison_table" — side-by-side features
- "pros_cons" — balanced analysis with confidence scores
- "swot_analysis" — four-quadrant strategic view
- "key_insights" — ranked takeaways
- "knowledge_map" — concept connections
- "timeline" — chronological events
"""


def _build_message_history(session: Session, user_message: str, attachments: list[dict] | None = None) -> list[genai_types.Content]:
    """Build message history for the Gemini API call."""
    contents: list[genai_types.Content] = []

    # Include recent conversation history (last 20 messages for context window efficiency)
    recent_messages = session.messages[-20:]
    for msg in recent_messages:
        role = "user" if msg.role == MessageRole.USER else "model"
        contents.append(genai_types.Content(
            role=role,
            parts=[genai_types.Part.from_text(text=msg.content)],
        ))

    # Build current message parts
    parts: list[genai_types.Part] = [genai_types.Part.from_text(text=user_message)]

    # Process attachments
    if attachments:
        for attachment in attachments:
            if attachment.get("type") == "text":
                parts.append(genai_types.Part.from_text(
                    text=f"\n\n[Attached Data]:\n{attachment.get('content', '')}"
                ))
            elif attachment.get("type") == "url":
                parts.append(genai_types.Part.from_text(
                    text=f"\n\n[URL to analyze]: {attachment.get('content', '')}"
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
                        text=f"\n\n[Image attachment could not be processed]"
                    ))

    contents.append(genai_types.Content(role="user", parts=parts))
    return contents


def _extract_synthesis(text: str) -> list[dict[str, Any]]:
    """Extract synthesis JSON blocks from agent response."""
    synthesis = []
    # Look for ```json blocks in the response
    import re
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

    if current == ConversationPhase.CLARIFICATION and msg_count >= 5:
        # After enough clarification, move to ingestion
        if any(kw in lower_response for kw in ["understand", "got it", "great", "let me summarize", "share any data"]):
            return ConversationPhase.INGESTION

    if current == ConversationPhase.INGESTION:
        if any(kw in lower_msg for kw in ["synthesize", "analyze", "compare", "ready", "that's all", "no more", "go ahead"]):
            return ConversationPhase.SYNTHESIS
        if msg_count >= 10:  # Auto-advance after enough data
            return ConversationPhase.SYNTHESIS

    if current == ConversationPhase.SYNTHESIS and "```json" in agent_response:
        return ConversationPhase.FEEDBACK

    if current == ConversationPhase.FEEDBACK:
        if any(kw in lower_msg for kw in ["new topic", "start over", "different", "another"]):
            return ConversationPhase.ONBOARDING
        if any(kw in lower_msg for kw in ["more", "refine", "update", "change", "add"]):
            return ConversationPhase.INGESTION

    return current


# ─── API Routes ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "synthmind",
        "model": settings.gemini_model,
        "version": "1.0.0",
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint — send a message, get an agent response."""
    trace_id = str(uuid.uuid4())[:8]
    current_trace_id.set(trace_id)

    # Get or create session
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

    # Add user message to session
    session.add_message(MessageRole.USER, request.message, "text")

    # Process attachments as ingested data
    for attachment in request.attachments:
        if attachment.get("type") in ("url", "text"):
            session.ingested_data.append({
                "type": attachment["type"],
                "content": attachment.get("content", "")[:5000],
                "title": attachment.get("title", "User-provided data"),
                "summary": attachment.get("content", "")[:200],
            })

    # Run the agent
    result = await run_agent(session, request.message, request.attachments)

    # Update session title from first meaningful message
    if len(session.messages) <= 2 and request.message and len(request.message) > 5:
        session.title = request.message[:80]

    # Save session
    await memory.save_session(session)

    return ChatResponse(
        session_id=session.id,
        message=result["message"],
        message_type=result["message_type"],
        synthesis=result["synthesis"],
        phase=result["phase"],
        trace_id=result["trace_id"],
    )


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

    # Read file content
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)

    if file_size_mb > settings.max_file_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum: {settings.max_file_size_mb}MB",
        )

    # Get or create session
    session = None
    if session_id:
        session = await memory.load_session(session_id)
    if session is None:
        session = Session(user_id=user_id)

    # Determine file type and process with Gemini
    mime_type = file.content_type or "application/octet-stream"
    filename = file.filename

    try:
        # Use Gemini to process the file
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

        # Parse extraction result
        extracted = {"title": filename, "summary": "File processed", "key_facts": [], "source_type": "file"}
        if response.text:
            try:
                # Try to parse JSON from response
                import re
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    extracted.update(parsed)
            except (json.JSONDecodeError, AttributeError):
                extracted["summary"] = response.text[:500]

        # Store in session
        extracted["source_name"] = filename
        extracted["source_type"] = mime_type.split("/")[0]  # image, application, text
        session.ingested_data.append(extracted)

        # Add system message about the upload
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


# ─── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
