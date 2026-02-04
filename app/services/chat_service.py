"""
Chat service for MI practice sessions using OpenAI API.
Handles session management, LLM interaction, and conversation history.
"""
import os
import uuid
import httpx
from datetime import datetime
from typing import Dict, Any, List, Optional
from .personas import get_persona, get_all_personas


# In-memory session storage
SESSIONS: Dict[str, Dict[str, Any]] = {}

# OpenAI API configuration
OPENAI_API_URL = "https://api.openai.com/v1/responses"


def _get_openai_model() -> str:
    """Get OpenAI model from environment, defaulting to gpt-4.1-mini."""
    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

# Maximum turns before session ends
MAX_TURNS = 20


def _get_openai_key() -> str:
    """Get OpenAI API key from environment."""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return key


def _build_system_prompt(persona: Dict[str, Any], turn_number: int, conversation_summary: str = "") -> str:
    """Build the system prompt for the persona."""

    summary_context = ""
    if conversation_summary:
        summary_context = f"""
CONVERSATION CONTEXT (Summary of earlier conversation):
{conversation_summary}
"""

    return f"""You are roleplaying as {persona['name']}, a {persona['age']}-year-old client in a
Motivational Interviewing practice session.

{persona['core_identity']}

CURRENT STATE:
- Stage of change: {persona['stage_of_change']}
- Initial mood: {persona['initial_mood']}
- Current turn: {turn_number} of {MAX_TURNS}

AMBIVALENCE (reasons for NOT changing):
{chr(10).join('- ' + point for point in persona['ambivalence_points'])}

MOTIVATION (reasons FOR changing):
{chr(10).join('- ' + point for point in persona['motivation_points'])}

{summary_context}

{persona['behavior_guidelines']}

RESPONSE GUIDELINES:
1. Stay completely in character as {persona['name']}
2. Respond naturally, as a real person would in a helping conversation
3. Keep responses conversational - typically 1-3 sentences, occasionally longer for emotional moments
4. Show realistic ambivalence - you're not sure about changing yet
5. React authentically to how the practitioner speaks to you
6. If asked direct questions, answer them but may show hesitation or redirect
7. As the conversation progresses and IF the practitioner is supportive, gradually open up more
8. Never break character or mention that this is a practice session
9. Never explicitly comment on the practitioner's techniques
10. Show emotion where appropriate - frustration, hope, doubt, fear, determination

Remember: You are {persona['name']}, not an AI. Respond as they would."""


def _summarize_conversation(history: List[Dict[str, str]], max_messages: int = 6) -> tuple[List[Dict[str, str]], str]:
    """
    Manage conversation context to reduce token usage.
    Returns recent messages and a summary of earlier conversation.

    Strategy: Keep last N messages in full, summarize earlier ones.
    """
    if len(history) <= max_messages:
        return history, ""

    # Split into older and recent messages
    older_messages = history[:-max_messages]
    recent_messages = history[-max_messages:]

    # Create a simple summary of older messages
    summary_parts = []
    for msg in older_messages:
        role = "Practitioner" if msg["role"] == "user" else "Client"
        # Truncate long messages in summary
        content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
        summary_parts.append(f"{role}: {content}")

    summary = "\n".join(summary_parts)

    return recent_messages, summary


async def start_session(persona_id: str) -> Dict[str, Any]:
    """Start a new chat practice session."""
    persona = get_persona(persona_id)
    if not persona:
        raise ValueError(f"Persona '{persona_id}' not found")

    session_id = str(uuid.uuid4())

    session = {
        "id": session_id,
        "persona_id": persona_id,
        "persona": persona,
        "history": [],
        "turn": 0,
        "started_at": datetime.utcnow(),
        "is_active": True
    }

    # Add the opening message to history
    session["history"].append({
        "role": "assistant",
        "content": persona["opening_message"]
    })

    SESSIONS[session_id] = session

    return {
        "session_id": session_id,
        "persona_name": persona["name"],
        "persona_title": persona["title"],
        "persona_avatar": persona["avatar"],
        "opening_message": persona["opening_message"],
        "max_turns": MAX_TURNS,
        "current_turn": 0
    }


async def send_message(session_id: str, user_message: str) -> Dict[str, Any]:
    """Process a user message and get persona response."""
    if session_id not in SESSIONS:
        raise ValueError(f"Session '{session_id}' not found")

    session = SESSIONS[session_id]

    if not session["is_active"]:
        raise ValueError("Session has ended")

    # Increment turn counter
    session["turn"] += 1
    current_turn = session["turn"]

    # Add user message to history
    session["history"].append({
        "role": "user",
        "content": user_message
    })

    # Check if this is the final turn
    is_final_turn = current_turn >= MAX_TURNS

    # Get conversation context (with summarization for long conversations)
    recent_history, conversation_summary = _summarize_conversation(session["history"])

    # Build the prompt
    system_prompt = _build_system_prompt(
        session["persona"],
        current_turn,
        conversation_summary
    )

    # Add special instruction for final turn
    if is_final_turn:
        system_prompt += """

IMPORTANT: This is the final turn of the conversation. Provide a natural closing response
that acknowledges where you are in your thinking about change. If the practitioner has been
helpful, express some appreciation. If not, you can express that the conversation wasn't
quite what you hoped for. Either way, bring the conversation to a natural close."""

    # Call OpenAI API
    try:
        response_text = await _call_openai(system_prompt, recent_history)
    except Exception as e:
        # On API error, provide a fallback response
        response_text = f"*pauses* I'm sorry, I got a bit distracted. Could you say that again?"
        print(f"OpenAI API error: {e}")

    # Add assistant response to history
    session["history"].append({
        "role": "assistant",
        "content": response_text
    })

    # Check if session is complete
    if is_final_turn:
        session["is_active"] = False

    result = {
        "response": response_text,
        "current_turn": current_turn,
        "max_turns": MAX_TURNS,
        "is_session_complete": is_final_turn,
        "session_summary": None
    }

    return result


async def _call_openai(system_prompt: str, messages: List[Dict[str, str]]) -> str:
    """Call OpenAI API using the responses endpoint."""
    api_key = _get_openai_key()

    # Build the input for the responses API
    # Format conversation as a single input with context
    conversation_text = f"System: {system_prompt}\n\n"
    for msg in messages:
        role = "Practitioner" if msg["role"] == "user" else "Client"
        conversation_text += f"{role}: {msg['content']}\n\n"

    conversation_text += "Client:"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": _get_openai_model(),
        "input": conversation_text,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            OPENAI_API_URL,
            headers=headers,
            json=payload
        )

        if response.status_code != 200:
            error_detail = response.text
            raise Exception(f"OpenAI API error: {response.status_code} - {error_detail}")

        data = response.json()

        # Extract response text from the API response
        # The responses API returns output in a specific format
        if "output" in data:
            output = data["output"]
            if isinstance(output, list) and len(output) > 0:
                # Handle structured output
                for item in output:
                    if item.get("type") == "message":
                        content = item.get("content", [])
                        for c in content:
                            if c.get("type") == "output_text":
                                return c.get("text", "").strip()
                            if c.get("type") == "text":
                                return c.get("text", "").strip()
            elif isinstance(output, str):
                return output.strip()

        # Fallback: try to find text in response
        if "text" in data:
            return data["text"].strip()

        # Another fallback for different response formats
        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0].get("message", {}).get("content", "").strip()

        raise Exception(f"Unexpected API response format: {data}")


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session data by ID."""
    return SESSIONS.get(session_id)


def get_session_transcript(session_id: str) -> List[Dict[str, str]]:
    """Get the full conversation transcript for a session."""
    session = SESSIONS.get(session_id)
    if not session:
        return []
    return session["history"]


def end_session(session_id: str) -> Dict[str, Any]:
    """End a session and return its data."""
    if session_id not in SESSIONS:
        raise ValueError(f"Session '{session_id}' not found")

    session = SESSIONS[session_id]
    session["is_active"] = False
    session["ended_at"] = datetime.utcnow()

    return {
        "session_id": session_id,
        "persona_id": session["persona_id"],
        "total_turns": session["turn"],
        "transcript": session["history"],
        "started_at": session["started_at"],
        "ended_at": session["ended_at"]
    }


def cleanup_old_sessions(max_age_hours: int = 24):
    """Clean up sessions older than specified hours."""
    cutoff = datetime.utcnow()
    to_remove = []

    for session_id, session in SESSIONS.items():
        age = (cutoff - session["started_at"]).total_seconds() / 3600
        if age > max_age_hours:
            to_remove.append(session_id)

    for session_id in to_remove:
        del SESSIONS[session_id]

    return len(to_remove)
