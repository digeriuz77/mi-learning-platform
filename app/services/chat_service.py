"""
Chat service for MI practice sessions using Fireworks AI.
Handles session management, LLM interaction, conversation history,
and optional database persistence.
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import settings
from .personas import get_persona

logger = logging.getLogger(__name__)

# In-memory session storage (fallback when DB unavailable)
SESSIONS: Dict[str, Dict[str, Any]] = {}

# Fireworks AI API configuration
FIREWORKS_API_URL = "https://api.fireworks.ai/inference/v1/chat/completions"

# Database persistence enabled flag
DB_PERSISTENCE_ENABLED = True


# Maximum turns before session ends
MAX_TURNS = 20
CONTEXT_WINDOW_MESSAGES = 10
SUMMARY_SNIPPET_LIMIT = 160
SUMMARY_MAX_BULLETS = 6
DEFAULT_INITIAL_MOOD = "guarded but open to talking"
CHAT_RESPONSE_MAX_TOKENS = 340
SENTENCE_ENDINGS = (".", "!", "?")
TRAILING_SENTENCE_CLOSERS = "\"'”’)]}"


def _get_supabase():
    """Get Supabase client for database operations."""
    try:
        from supabase import create_client

        return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    except Exception as e:
        logger.warning(f"Could not initialize Supabase client: {e}")
        return None


def _get_fireworks_key() -> str:
    """Get Fireworks API key from environment."""
    key = (os.getenv("FIREWORKS_API_KEY") or settings.FIREWORKS_API_KEY or "").strip()
    if not key:
        raise ValueError(
            "FIREWORKS_API_KEY environment variable is not set. Get your API key from https://fireworks.ai"
        )
    return key


def _get_dialect_instructions(persona: Dict[str, Any]) -> str:
    """Return lightweight dialect guidance for persona consistency."""
    dialect = str(persona.get("dialect") or "RP").strip().upper()
    if dialect == "RP":
        return "Use neutral British English with natural phrasing."
    return f"Use light {dialect} flavour naturally and sparingly."


def _compact_text(text: str, limit: int = SUMMARY_SNIPPET_LIMIT) -> str:
    """Normalize whitespace and trim to a compact snippet."""
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _ensure_complete_sentence(text: str) -> str:
    """Trim a response to a clean sentence boundary when truncation occurs."""
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    if cleaned.endswith((*SENTENCE_ENDINGS, "…")):
        return cleaned
    last_sentence_end = max(cleaned.rfind("."), cleaned.rfind("!"), cleaned.rfind("?"))
    if last_sentence_end != -1:
        end = last_sentence_end + 1
        while end < len(cleaned) and cleaned[end] in TRAILING_SENTENCE_CLOSERS:
            end += 1
        return cleaned[:end].strip()
    return cleaned.rstrip(" ,;:-—") + "."


def _dedupe_keep_recent(items: List[str], max_items: int) -> List[str]:
    """De-duplicate while preserving most recent entries."""
    seen = set()
    deduped: List[str] = []
    for item in reversed(items):
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= max_items:
            break
    deduped.reverse()
    return deduped


def _append_memory_item(memory_bucket: List[str], text: str, max_items: int = 5) -> None:
    """Append a compact memory item while preserving recency and uniqueness."""
    snippet = _compact_text(text, 140)
    if not snippet:
        return
    lowered = snippet.lower()
    if any(existing.lower() == lowered for existing in memory_bucket):
        return
    memory_bucket.append(snippet)
    while len(memory_bucket) > max_items:
        memory_bucket.pop(0)


def _build_session_memory(history: List[Dict[str, str]]) -> Dict[str, List[str]]:
    """Build compact rolling memory from transcript history."""
    memory: Dict[str, List[str]] = {
        "practitioner_focus": [],
        "client_barriers": [],
        "client_motivation": [],
    }
    for msg in history:
        content = str(msg.get("content", ""))
        role = msg.get("role")
        lowered = content.lower()
        if role == "user":
            _append_memory_item(memory["practitioner_focus"], content)
            continue
        if role != "assistant":
            continue
        if any(token in lowered for token in ["but", "can't", "cannot", "worried", "not sure", "hard"]):
            _append_memory_item(memory["client_barriers"], content)
        if any(token in lowered for token in ["i want", "i need", "i can", "i will", "i'm going to", "i should"]):
            _append_memory_item(memory["client_motivation"], content)
    return memory


def _format_session_memory(memory: Dict[str, List[str]]) -> str:
    """Format rolling memory for system prompt inclusion."""
    sections: List[str] = []
    focus = memory.get("practitioner_focus") or []
    barriers = memory.get("client_barriers") or []
    motivation = memory.get("client_motivation") or []
    if focus:
        sections.append("Practitioner focus so far:")
        sections.extend([f"- {item}" for item in focus])
    if barriers:
        sections.append("Client barriers/tension points:")
        sections.extend([f"- {item}" for item in barriers])
    if motivation:
        sections.append("Client motivations/commitments:")
        sections.extend([f"- {item}" for item in motivation])
    return "\n".join(sections)


def _build_system_prompt(
    persona: Dict[str, Any],
    turn_number: int,
    conversation_summary: str = "",
    rolling_memory: str = "",
) -> str:
    """Build the system prompt for the persona."""
    persona_name = persona.get("name", "Client")
    persona_age = persona.get("age", "adult")
    stage_of_change = persona.get("stage_of_change", "contemplation")
    initial_mood = persona.get("initial_mood") or DEFAULT_INITIAL_MOOD
    ambivalence_points = persona.get("ambivalence_points") or []
    motivation_points = persona.get("motivation_points") or []
    core_identity = persona.get("core_identity", "")
    behavior_guidelines = persona.get("behavior_guidelines", "")

    summary_context = ""
    if conversation_summary:
        summary_context = f"""
CONVERSATION CONTEXT (Summary of earlier conversation):
{conversation_summary}
"""

    memory_context = ""
    if rolling_memory:
        memory_context = f"""
ROLLING MEMORY (high-value details to stay consistent):
{rolling_memory}
"""

    dialect_instructions = _get_dialect_instructions(persona)

    return f"""You are roleplaying as {persona_name}, a {persona_age}-year-old client in a
Motivational Interviewing practice session.

{core_identity}

CURRENT STATE:
- Stage of change: {stage_of_change}
- Initial mood: {initial_mood}
- Current turn: {turn_number} of {MAX_TURNS}
- Dialect guidance: {dialect_instructions}

AMBIVALENCE (reasons for NOT changing):
{chr(10).join("- " + point for point in ambivalence_points)}

MOTIVATION (reasons FOR changing):
{chr(10).join("- " + point for point in motivation_points)}

{summary_context}
{memory_context}

{behavior_guidelines}

RESPONSE GUIDELINES:
1. Stay fully in character as {persona_name}; never mention being an AI or simulation.
2. Keep responses natural and concise (usually 1-3 sentences).
3. Reflect realistic ambivalence while responding to the practitioner's tone and approach.
4. If asked to go off-topic, politely redirect to your real dilemma and continue the conversation.
5. Never provide stage directions, bracketed actions, or analysis of MI techniques.
6. Use dialect markers sparingly and naturally.

Remember: You are {persona_name}. Respond exactly as this person would."""


def _summarize_conversation(
    history: List[Dict[str, str]], max_messages: int = CONTEXT_WINDOW_MESSAGES
) -> Tuple[List[Dict[str, str]], str]:
    """Manage conversation context by summarizing older turns."""
    if len(history) <= max_messages:
        return history, ""

    older_messages = history[:-max_messages]
    recent_messages = history[-max_messages:]

    practitioner_moves = _dedupe_keep_recent(
        [_compact_text(str(msg.get("content", ""))) for msg in older_messages if msg.get("role") == "user"],
        SUMMARY_MAX_BULLETS,
    )
    client_signals = _dedupe_keep_recent(
        [_compact_text(str(msg.get("content", ""))) for msg in older_messages if msg.get("role") == "assistant"],
        SUMMARY_MAX_BULLETS,
    )

    summary_lines: List[str] = []
    if practitioner_moves:
        summary_lines.append("Practitioner has already explored:")
        summary_lines.extend([f"- {item}" for item in practitioner_moves])
    if client_signals:
        summary_lines.append("Client has previously expressed:")
        summary_lines.extend([f"- {item}" for item in client_signals])

    summary = "\n".join(summary_lines)
    if len(summary) > 1800:
        summary = summary[:1797].rstrip() + "..."

    return recent_messages, summary


async def start_session(persona_id: str, user_id: str = None) -> Dict[str, Any]:
    """Start a new chat practice session.

    Args:
        persona_id: ID of the persona to practice with
        user_id: Authenticated user's ID (for session ownership validation)
    """
    persona = get_persona(persona_id)
    if not persona:
        raise ValueError(f"Persona '{persona_id}' not found")
    if not persona.get("initial_mood"):
        persona = {**persona, "initial_mood": DEFAULT_INITIAL_MOOD}

    session_id = str(uuid.uuid4())

    session = {
        "id": session_id,
        "persona_id": persona_id,
        "persona": persona,
        "history": [],
        "memory": {
            "practitioner_focus": [],
            "client_barriers": [],
            "client_motivation": [],
        },
        "turn": 0,
        "started_at": datetime.now(timezone.utc),
        "is_active": True,
        # P1-12: Track session owner for ownership validation
        "user_id": user_id,
    }

    # Add the opening message to history
    session["history"].append({"role": "assistant", "content": persona["opening_message"]})
    session["memory"] = _build_session_memory(session["history"])

    SESSIONS[session_id] = session

    # Persist to database
    _save_session_to_db(session)

    return {
        "session_id": session_id,
        "persona_name": persona["name"],
        "persona_title": persona["title"],
        "persona_avatar": persona["avatar"],
        "opening_message": persona["opening_message"],
        "max_turns": MAX_TURNS,
        "current_turn": 0,
    }


def validate_session_owner(session_id: str, user_id: str) -> bool:
    """P1-12: Validate that the authenticated user owns the session.

    Returns True if the session belongs to the user or has no owner set.
    Raises ValueError if session not found or user doesn't own it.
    """
    if session_id not in SESSIONS:
        db_session = _load_session_from_db(session_id)
        if db_session:
            SESSIONS[session_id] = db_session
        else:
            raise ValueError(f"Session '{session_id}' not found")
    session = SESSIONS[session_id]
    # Allow if no user_id was set (backward compatibility) or if it matches
    if session.get("user_id") and session["user_id"] != user_id:
        raise ValueError("You do not have access to this session")
    return True


async def send_message(session_id: str, user_message: str) -> Dict[str, Any]:
    """Process a user message and get persona response."""
    # Try in-memory first, then DB
    if session_id not in SESSIONS:
        db_session = _load_session_from_db(session_id)
        if db_session:
            SESSIONS[session_id] = db_session
        else:
            raise ValueError(f"Session '{session_id}' not found")

    session = SESSIONS[session_id]

    if not session["is_active"]:
        raise ValueError("Session has ended")

    # Increment turn counter
    session["turn"] += 1
    current_turn = session["turn"]

    # Add user message to history
    session["history"].append({"role": "user", "content": user_message})
    session["memory"] = _build_session_memory(session["history"])

    # Check if this is the final turn
    is_final_turn = current_turn >= MAX_TURNS

    # Get conversation context (with summarization for long conversations)
    recent_history, conversation_summary = _summarize_conversation(session["history"])
    rolling_memory = _format_session_memory(session.get("memory", {}))

    # Build the prompt
    system_prompt = _build_system_prompt(
        session["persona"], current_turn, conversation_summary, rolling_memory
    )

    # Add special instruction for final turn
    if is_final_turn:
        system_prompt += """

IMPORTANT: This is the final turn of the conversation. Provide a natural closing response
that acknowledges where you are in your thinking about change. If the practitioner has been
helpful, express some appreciation. If not, you can express that the conversation wasn't
quite what you hoped for. Either way, bring the conversation to a natural close."""

    # Call Fireworks API
    try:
        response_text = await _call_fireworks(system_prompt, recent_history)
    except Exception as error:
        # On API error, provide a fallback response
        response_text = "*pauses* I'm sorry, I got a bit distracted. Could you say that again?"
        logger.warning(f"Fireworks API error in chat session: {type(error).__name__}")

    # Add assistant response to history
    session["history"].append({"role": "assistant", "content": response_text})
    session["memory"] = _build_session_memory(session["history"])

    # Check if session is complete
    if is_final_turn:
        session["is_active"] = False

    # Persist to database
    _save_session_to_db(session)

    result = {
        "response": response_text,
        "current_turn": current_turn,
        "max_turns": MAX_TURNS,
        "is_session_complete": is_final_turn,
        "session_summary": None,
    }

    return result


async def _call_fireworks(system_prompt: str, messages: List[Dict[str, str]]) -> str:
    """Call Fireworks AI API using the chat completions endpoint."""
    api_key = _get_fireworks_key()

    if not api_key or api_key.strip() in {
        "",
        "your_fireworks_api_key_here",
        "your_fireworks_api_key",
    }:
        raise ValueError(
            "FIREWORKS_API_KEY environment variable is not set. Get your API key from https://fireworks.ai"
        )

    # Build messages array for chat completions format
    chat_messages = [{"role": "system", "content": system_prompt}]

    for msg in messages:
        role = "user" if msg["role"] == "user" else "assistant"
        chat_messages.append({"role": role, "content": msg["content"]})

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = {
        "model": settings.FIREWORKS_MODEL,
        "messages": chat_messages,
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": CHAT_RESPONSE_MAX_TOKENS,
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(FIREWORKS_API_URL, headers=headers, json=payload)

        if response.status_code != 200:
            raise Exception(f"Fireworks API error: {response.status_code}")

        data = response.json()

        # Fireworks uses OpenAI-compatible format
        if "choices" in data and len(data["choices"]) > 0:
            choice = data["choices"][0]
            content = choice.get("message", {}).get("content", "").strip()
            finish_reason = str(choice.get("finish_reason") or "").lower()
            if finish_reason == "length":
                logger.info("Chat response hit token limit; trimming to sentence boundary")
                return _ensure_complete_sentence(content)
            return content

        raise Exception(f"Unexpected API response format: {data}")


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session data by ID."""
    if session_id in SESSIONS:
        return SESSIONS.get(session_id)
    # Try loading from database
    db_session = _load_session_from_db(session_id)
    if db_session:
        SESSIONS[session_id] = db_session
        return db_session
    return None


def get_session_transcript(session_id: str) -> List[Dict[str, str]]:
    """Get the full conversation transcript for a session."""
    session = get_session(session_id)
    if not session:
        return []
    return session["history"]


def end_session(session_id: str) -> Dict[str, Any]:
    """End a session and return its data."""
    if session_id not in SESSIONS:
        db_session = _load_session_from_db(session_id)
        if db_session:
            SESSIONS[session_id] = db_session
        else:
            raise ValueError(f"Session '{session_id}' not found")

    session = SESSIONS[session_id]
    session["is_active"] = False
    session["ended_at"] = datetime.now(timezone.utc)

    # Persist to database and delete
    _save_session_to_db(session)
    _delete_session_from_db(session_id)

    return {
        "session_id": session_id,
        "persona_id": session["persona_id"],
        "total_turns": session["turn"],
        "transcript": session["history"],
        "started_at": session["started_at"],
        "ended_at": session["ended_at"],
    }


def cleanup_old_sessions(max_age_hours: int = 24):
    """Clean up sessions older than specified hours."""
    cutoff = datetime.now(timezone.utc)
    to_remove = []

    for session_id, session in SESSIONS.items():
        started_at = session.get("started_at")
        if isinstance(started_at, str):
            try:
                started_at = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            except Exception:
                continue
        if not isinstance(started_at, datetime):
            continue
        age = (cutoff - started_at).total_seconds() / 3600
        if age > max_age_hours:
            to_remove.append(session_id)

    for session_id in to_remove:
        del SESSIONS[session_id]

    return len(to_remove)


# ==================== Database Persistence Functions ====================


def _save_session_to_db(session: Dict[str, Any]) -> bool:
    """Save session to database. Returns True if successful."""
    if not DB_PERSISTENCE_ENABLED:
        return False

    supabase = _get_supabase()
    if not supabase:
        return False

    try:
        started_at = session["started_at"]
        ended_at = session.get("ended_at")

        session_data = {
            "session_id": session["id"],
            "user_id": session.get("user_id"),
            "persona_id": session["persona_id"],
            "persona_data": session["persona"],
            "history": session["history"],
            "turn": session["turn"],
            "is_active": session["is_active"],
            "started_at": started_at.isoformat() if isinstance(started_at, datetime) else started_at,
            "ended_at": ended_at.isoformat() if ended_at and isinstance(ended_at, datetime) else ended_at,
        }

        supabase.table("chat_sessions").upsert(session_data).execute()
        return True
    except Exception as e:
        logger.warning(f"Failed to save session to DB: {e}")
        return False


def _load_session_from_db(session_id: str) -> Optional[Dict[str, Any]]:
    """Load session from database. Returns session dict or None."""
    supabase = _get_supabase()
    if not supabase:
        return None

    try:
        result = supabase.table("chat_sessions").select("*").eq("session_id", session_id).maybe_single().execute()
        if result.data is None:
            return None
        data = result.data
        history = data.get("history") or []
        return {
            "id": data["session_id"],
            "session_id": data["session_id"],
            "user_id": data.get("user_id"),
            "persona_id": data["persona_id"],
            "persona": data["persona_data"],
            "history": history,
            "memory": _build_session_memory(history),
            "turn": data["turn"] or 0,
            "is_active": data["is_active"],
            "started_at": data["started_at"],
            "ended_at": data.get("ended_at"),
        }
    except Exception as e:
        logger.warning(f"Failed to load session from DB: {e}")
        return None


def _delete_session_from_db(session_id: str) -> bool:
    """Delete session from database. Returns True if successful."""
    if not DB_PERSISTENCE_ENABLED:
        return False

    supabase = _get_supabase()
    if not supabase:
        return False

    try:
        supabase.table("chat_sessions").delete().eq("session_id", session_id).execute()
        return True
    except Exception as e:
        logger.warning(f"Failed to delete session from DB: {e}")
        return False
