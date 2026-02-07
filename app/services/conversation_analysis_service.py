"""
Conversation Analysis Service for MI Practice Sessions.
Analyzes conversations using MAPS framework and MI technique detection.
"""

import os
import httpx
import json
from typing import Dict, Any, List, Optional


OPENAI_API_URL = "https://api.openai.com/v1/responses"


def _get_openai_model() -> str:
    """Get OpenAI model from environment, defaulting to gpt-4.1-mini."""
    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def _get_openai_key() -> str:
    """Get OpenAI API key from environment."""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return key


ANALYSIS_PROMPT = """You are an expert Motivational Interviewing (MI) trainer and assessor.
Analyze the following practice conversation between a practitioner learning MI and a simulated client.

Your task is to provide detailed, constructive feedback based on the MAPS (Money and Pensions Service)
person-centred coaching framework and MI principles.

ANALYSIS FRAMEWORK:

1. MAPS Core Dimensions (score each 1-5):
   - Foundational Trust & Safety: Did the practitioner create psychological safety? Were they
     authentic and non-judgmental?
   - Empathic Partnership & Autonomy: Did they demonstrate genuine empathy while respecting
     the client's autonomy and right to make their own choices?
   - Empowerment & Clarity: Did they help the client feel capable? Was the path forward clearer?

2. MI Spirit Assessment:
   - Partnership: Collaborative rather than prescriptive
   - Acceptance: Unconditional positive regard, autonomy support
   - Compassion: Genuine care for client wellbeing
   - Evocation: Drawing out client's own motivations rather than imposing

3. MI Techniques to identify:
   - Open Questions: Questions that invite elaboration
   - Affirmations: Genuine acknowledgment of strengths/efforts
   - Reflections: Simple (repeat/rephrase) and Complex (add meaning/emotion)
   - Summaries: Pulling together what the client has shared
   - OARS overall balance

4. Non-MI Behaviors to identify:
   - Giving unsolicited advice
   - Confrontation or argumentation
   - Directing without permission
   - Judging or criticizing
   - Closed questions that limit exploration

5. Client Movement:
   - Did the client move toward change talk?
   - Did they become more open or more resistant?
   - Were there any breakthrough moments?

CONVERSATION TO ANALYZE:
{conversation}

Please provide your analysis in the following JSON format (ensure valid JSON):
{{
    "overall_score": <1-5 float>,
    "foundational_trust_safety": <1-5 float>,
    "empathic_partnership_autonomy": <1-5 float>,
    "empowerment_clarity": <1-5 float>,
    "mi_spirit_score": <1-5 float>,
    "partnership_demonstrated": <true/false>,
    "acceptance_demonstrated": <true/false>,
    "compassion_demonstrated": <true/false>,
    "evocation_demonstrated": <true/false>,
    "techniques_used": [
        {{
            "technique": "<technique name>",
            "turn_number": <turn number>,
            "example": "<brief quote or paraphrase>",
            "effectiveness": "<effective/partially_effective/ineffective>"
        }}
    ],
    "techniques_count": {{
        "open_question": <count>,
        "closed_question": <count>,
        "simple_reflection": <count>,
        "complex_reflection": <count>,
        "affirmation": <count>,
        "summary": <count>,
        "giving_advice": <count>,
        "directing": <count>
    }},
    "strengths": ["<strength 1>", "<strength 2>", ...],
    "areas_for_improvement": ["<area 1>", "<area 2>", ...],
    "client_movement": "<toward_change/stable/away_from_change>",
    "change_talk_evoked": <true/false>,
    "transcript_summary": "<1-2 paragraph summary of what actually happened in the conversation - the key topics discussed, how the client responded, and the flow of dialogue>",
    "summary": "<2-3 paragraph summary of the conversation quality and practitioner performance>",
    "key_moments": [
        {{
            "turn": <turn number>,
            "moment": "<description of what happened>",
            "impact": "<positive/negative/neutral>"
        }}
    ],
    "suggestions_for_next_time": ["<suggestion 1>", "<suggestion 2>", ...]
}}

Be specific in your feedback with examples from the conversation. Be constructive and educational -
the goal is to help the practitioner improve their MI skills."""


def _format_conversation(transcript: List[Dict[str, str]], persona_name: str) -> str:
    """Format conversation transcript for analysis."""
    formatted_lines = []
    turn = 0

    for i, msg in enumerate(transcript):
        if msg["role"] == "user":
            turn += 1
            formatted_lines.append(f"[Turn {turn}] Practitioner: {msg['content']}")
        else:
            formatted_lines.append(f"[Turn {turn}] {persona_name}: {msg['content']}")

    return "\n\n".join(formatted_lines)


async def analyze_conversation(
    transcript: List[Dict[str, str]], persona_name: str = "Client"
) -> Dict[str, Any]:
    """
    Analyze a practice conversation and return detailed feedback.

    Args:
        transcript: List of messages with 'role' and 'content' keys
        persona_name: Name of the client persona for formatting

    Returns:
        Detailed analysis dictionary
    """
    api_key = _get_openai_key()

    # Format the conversation
    formatted_conversation = _format_conversation(transcript, persona_name)

    # Build the analysis request
    prompt = ANALYSIS_PROMPT.format(conversation=formatted_conversation)

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    payload = {
        "model": _get_openai_model(),
        "input": prompt,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(OPENAI_API_URL, headers=headers, json=payload)

        if response.status_code != 200:
            error_detail = response.text
            raise Exception(
                f"OpenAI API error: {response.status_code} - {error_detail}"
            )

        data = response.json()

        # Extract response text
        response_text = _extract_response_text(data)

        # Parse JSON from response
        analysis = _parse_analysis_json(response_text)

        return analysis


def _extract_response_text(data: Dict[str, Any]) -> str:
    """Extract text from OpenAI API response."""
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

    if "choices" in data and len(data["choices"]) > 0:
        return data["choices"][0].get("message", {}).get("content", "").strip()

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
    except json.JSONDecodeError as e:
        # If parsing fails, return a default structure with error info
        return _get_default_analysis(f"Failed to parse analysis: {str(e)}")


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
        "summary": error_message
        or "Analysis could not be generated. Please try again.",
        "key_moments": [],
        "suggestions_for_next_time": [
            "Practice with longer conversations for more detailed feedback"
        ],
    }


def calculate_technique_balance(techniques_count: Dict[str, int]) -> Dict[str, Any]:
    """Calculate OARS balance and other technique metrics."""
    oars = {
        "open_questions": techniques_count.get("open_question", 0),
        "affirmations": techniques_count.get("affirmation", 0),
        "reflections": techniques_count.get("simple_reflection", 0)
        + techniques_count.get("complex_reflection", 0),
        "summaries": techniques_count.get("summary", 0),
    }

    total_oars = sum(oars.values())
    non_mi = techniques_count.get("giving_advice", 0) + techniques_count.get(
        "directing", 0
    )

    # Calculate reflection to question ratio
    total_questions = techniques_count.get("open_question", 0) + techniques_count.get(
        "closed_question", 0
    )
    reflection_ratio = (
        oars["reflections"] / total_questions if total_questions > 0 else 0
    )

    # Calculate open vs closed question ratio
    open_question_ratio = (
        techniques_count.get("open_question", 0) / total_questions
        if total_questions > 0
        else 0
    )

    return {
        "oars_breakdown": oars,
        "total_oars": total_oars,
        "non_mi_behaviors": non_mi,
        "reflection_to_question_ratio": round(reflection_ratio, 2),
        "open_question_percentage": round(open_question_ratio * 100, 1),
        "mi_adherent_percentage": round(
            total_oars / (total_oars + non_mi) * 100
            if (total_oars + non_mi) > 0
            else 0,
            1,
        ),
    }
