"""
Conversation Analysis Service for MI Practice Sessions.
Analyzes conversations using MAPS framework and MI technique detection.
Uses Fireworks AI for LLM-based analysis.
"""

import json
import os
from typing import Dict, Any, List, Optional

import httpx

from app.config import settings

# Fireworks AI API configuration
FIREWORKS_API_URL = "https://api.fireworks.ai/inference/v1/chat/completions"
MAX_ANALYSIS_MESSAGES = 36
MAX_ANALYSIS_HEAD_MESSAGES = 8
MAX_ANALYSIS_TAIL_MESSAGES = 24
MAX_ANALYSIS_CHARS_PER_MESSAGE = 220
MAX_ANALYSIS_CONVERSATION_CHARS = 6500
ANALYSIS_RESPONSE_MAX_TOKENS = 2200


def _get_fireworks_key() -> str:
    """Get Fireworks API key from environment."""
    key = (os.getenv("FIREWORKS_API_KEY") or settings.FIREWORKS_API_KEY or "").strip()
    if not key:
        raise ValueError(
            "FIREWORKS_API_KEY environment variable is not set. Get your API key from https://fireworks.ai"
        )
    return key


ANALYSIS_SYSTEM_PROMPT = """You are an expert Motivational Interviewing (MI) assessor for MAPS.
Return ONLY valid JSON (no markdown) that matches this structure exactly:
{
  "overall_score": 1-5 float,
  "foundational_trust_safety": 1-5 float,
  "empathic_partnership_autonomy": 1-5 float,
  "empowerment_clarity": 1-5 float,
  "mi_spirit_score": 1-5 float,
  "partnership_demonstrated": bool,
  "acceptance_demonstrated": bool,
  "compassion_demonstrated": bool,
  "evocation_demonstrated": bool,
  "techniques_used": [{"technique": str, "turn_number": int, "example": str, "effectiveness": "effective|partially_effective|ineffective"}],
  "techniques_count": {"open_question": int, "closed_question": int, "simple_reflection": int, "complex_reflection": int, "affirmation": int, "summary": int, "giving_advice": int, "directing": int},
  "strengths": [str],
  "areas_for_improvement": [str],
  "client_movement": "toward_change|stable|away_from_change",
  "change_talk_evoked": bool,
  "transcript_summary": str,
  "summary": str,
  "key_moments": [{"turn": int, "moment": str, "impact": "positive|negative|neutral"}],
  "suggestions_for_next_time": [str]
}
Rules:
- Ground feedback in transcript evidence.
- Keep examples concise and specific.
- Include enough depth to be actionable and educational."""

ANALYSIS_USER_PROMPT = """Persona: {persona_name}
Transcript:
{conversation}"""


def _compact_message_text(text: str, limit: int = MAX_ANALYSIS_CHARS_PER_MESSAGE) -> str:
    """Normalize and trim message content for analysis efficiency."""
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _format_conversation(transcript: List[Dict[str, str]], persona_name: str) -> str:
    """Format transcript as compact turn lines for token-efficient analysis."""
    lines: List[str] = []
    turn = 0

    for msg in transcript:
        role = msg.get("role")
        if role not in {"user", "assistant"}:
            continue
        content = _compact_message_text(str(msg.get("content", "")))
        if not content:
            continue
        if role == "user":
            turn += 1
            lines.append(f"[T{turn}] Practitioner: {content}")
        else:
            visible_turn = turn if turn > 0 else 1
            lines.append(f"[T{visible_turn}] {persona_name}: {content}")

    if len(lines) > MAX_ANALYSIS_MESSAGES:
        head = lines[:MAX_ANALYSIS_HEAD_MESSAGES]
        tail = lines[-MAX_ANALYSIS_TAIL_MESSAGES:]
        omitted = len(lines) - len(head) - len(tail)
        lines = [
            *head,
            f"[... {omitted} earlier messages omitted for brevity ...]",
            *tail,
        ]

    conversation = "\n".join(lines)
    if len(conversation) > MAX_ANALYSIS_CONVERSATION_CHARS:
        conversation = conversation[: MAX_ANALYSIS_CONVERSATION_CHARS - 1].rstrip() + "…"

    return conversation


async def analyze_conversation(transcript: List[Dict[str, str]], persona_name: str = "Client") -> Dict[str, Any]:
    """
    Analyze a practice conversation and return detailed feedback.

    Args:
        transcript: List of messages with 'role' and 'content' keys
        persona_name: Name of the client persona for formatting

    Returns:
        Detailed analysis dictionary
    """
    api_key = _get_fireworks_key()

    # Format the conversation
    formatted_conversation = _format_conversation(transcript, persona_name)

    # Build the analysis request
    prompt = ANALYSIS_USER_PROMPT.format(
        persona_name=persona_name, conversation=formatted_conversation
    )

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    # Use Fireworks chat completions format
    payload = {
        "model": settings.FIREWORKS_MODEL,
        "messages": [
            {
                "role": "system",
                "content": ANALYSIS_SYSTEM_PROMPT,
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "top_p": 0.9,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(FIREWORKS_API_URL, headers=headers, json=payload)

        if response.status_code != 200:
            raise Exception(f"Fireworks API error: {response.status_code}")

        data = response.json()

        # Extract response text
        response_text = _extract_response_text(data)

        # Parse JSON from response
        analysis = _parse_analysis_json(response_text)

    analysis["technique_balance"] = calculate_technique_balance(analysis.get("techniques_count", {}))
    return analysis


def get_default_analysis(error_message: Optional[str] = None) -> Dict[str, Any]:
    """Return a default analysis structure when parsing fails, with technique_balance."""
    analysis = _get_default_analysis(error_message)
    analysis["technique_balance"] = calculate_technique_balance(analysis.get("techniques_count", {}))
    return analysis


def _extract_response_text(data: Dict[str, Any]) -> str:
    """Extract text from Fireworks API response."""
    # Fireworks uses OpenAI-compatible format
    if "choices" in data and len(data["choices"]) > 0:
        choice = data["choices"][0]
        if "message" in choice:
            return choice["message"].get("content", "").strip()
        if "text" in choice:
            return choice["text"].strip()

    # Fallback to other formats
    if "output" in data:
        output = data["output"]
        if isinstance(output, list) and len(output) > 0:
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

    if "text" in data:
        return data["text"].strip()

    raise Exception(f"Unexpected API response format: {data}")


def _parse_analysis_json(response_text: str) -> Dict[str, Any]:
    """Parse JSON from the analysis response."""
    # Try to find JSON in the response
    # Sometimes the model wraps it in markdown code blocks
    text = response_text.strip()

    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Retry by extracting the first JSON object when the model adds wrappers.
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError as e:
                return get_default_analysis(f"Failed to parse analysis: {str(e)}")
        return get_default_analysis("Failed to parse analysis: no valid JSON object found")


def _get_default_analysis(error_message: Optional[str] = None) -> Dict[str, Any]:
    """Return a default analysis structure when parsing fails."""
    return {
        "overall_score": 3.0,
        "foundational_trust_safety": 3.0,
        "empathic_partnership_autonomy": 3.0,
        "empowerment_clarity": 3.0,
        "mi_spirit_score": 3.0,
        "partnership_demonstrated": False,
        "acceptance_demonstrated": False,
        "compassion_demonstrated": False,
        "evocation_demonstrated": False,
        "techniques_used": [],
        "techniques_count": {
            "open_question": 0,
            "closed_question": 0,
            "simple_reflection": 0,
            "complex_reflection": 0,
            "affirmation": 0,
            "summary": 0,
            "giving_advice": 0,
            "directing": 0,
        },
        "strengths": ["Analysis could not be completed"],
        "areas_for_improvement": ["Please try again"],
        "client_movement": "stable",
        "change_talk_evoked": False,
        "transcript_summary": "Analysis could not be generated. Please try again.",
        "summary": error_message or "Analysis could not be generated. Please try again.",
        "key_moments": [],
        "suggestions_for_next_time": ["Practice with longer conversations for more detailed feedback"],
    }


def calculate_technique_balance(techniques_count: Dict[str, int]) -> Dict[str, Any]:
    """Calculate OARS balance and other technique metrics."""
    oars = {
        "open_questions": techniques_count.get("open_question", 0),
        "affirmations": techniques_count.get("affirmation", 0),
        "reflections": techniques_count.get("simple_reflection", 0) + techniques_count.get("complex_reflection", 0),
        "summaries": techniques_count.get("summary", 0),
    }

    total_oars = sum(oars.values())
    non_mi = techniques_count.get("giving_advice", 0) + techniques_count.get("directing", 0)

    # Calculate reflection to question ratio
    total_questions = techniques_count.get("open_question", 0) + techniques_count.get("closed_question", 0)
    reflection_ratio = oars["reflections"] / total_questions if total_questions > 0 else 0

    # Calculate open vs closed question ratio
    open_question_ratio = techniques_count.get("open_question", 0) / total_questions if total_questions > 0 else 0

    return {
        "oars_breakdown": oars,
        "total_oars": total_oars,
        "non_mi_behaviors": non_mi,
        "reflection_to_question_ratio": round(reflection_ratio, 2),
        "open_question_percentage": round(open_question_ratio * 100, 1),
        "mi_adherent_percentage": round(
            total_oars / (total_oars + non_mi) * 100 if (total_oars + non_mi) > 0 else 0,
            1,
        ),
    }
