# Smoking Cessation Chat Architecture

## Current Implementation Summary

### How It Works

The app uses a **Unified Chat Architecture** with these key components:

**Core Flow:**
1. `POST /api/chat/start` - Creates session, fetches persona from database, generates opening message
2. `POST /api/chat/message` - Processes user message through LLM, updates trust/mood, stores in database
3. `POST /api/chat/end` - Finalizes session, returns summary

**Key Services:**
- `UnifiedChatService` - Main orchestration
- `LLMService` - OpenAI/Anthropic/Gemini integration
- `MemoryScoringService` - Retrieves relevant memories
- `TrustConfigurationService` - Manages trust delta calculations

**Database Tables Used:**
- `conversations` - Session records
- `conversation_transcripts` - Message history
- `enhanced_personas` - Persona definitions
- `long_term_memories` - Persistent memories
- `character_knowledge_tiers` - Trust-gated knowledge

---

## Prompt-Driven Architecture (No Database)

### Simplified Approach

```python
# Single file: prompt_driven_chat.py

SYSTEM_PROMPT = """
You are {persona_name}, a smoking cessation coach. You are {mood}.

Persona profile:
- Core identity: {core_identity}
- Stage of change: {stage_of_change}
- Current trust level: {trust_level}/100
- Recent context: {memory_context}

Guidelines:
- Keep responses conversational and empathetic
- Ask clarifying questions when unsure
- Adapt tone based on trust level
- Reference shared context from this conversation
- Current turn: {turn_number}
"""

async def chat(user_message: str, history: list[dict]) -> dict:
    context = build_context(history)
    response = await llm.complete(SYSTEM_PROMPT.format(**context), history)
    return {
        "response": response,
        "trust_change": calculate_trust(response, user_message)
    }
```

### Minimal Implementation

| Component | Current | Simplified |
|-----------|---------|------------|
| Session | Database + UUID | In-memory dict |
| Messages | Database table | List in memory |
| Personas | Database table | Hardcoded JSON |
| Memory | 4 database tables | Rolling context window |
| Trust | Database field | Calculated per-turn |
| Mood | Database + transitions | Derived from trust |

### Key Files

```
prompt_driven_chat/
├── chat.py              # Main logic (single file)
├── personas.py          # Persona definitions
├── history.json         # Optional: persist to file
└── requirements.txt     # openai>=1.0.0
```

### Core Functions

```python
# 1. Start session
def start_session(persona_id: str) -> str:
    session = {
        "persona": PERSONAS[persona_id],
        "history": [],
        "trust": 0.5,
        "turn": 0
    }
    return session_id

# 2. Send message
async def send_message(session_id: str, message: str) -> dict:
    session = SESSIONS[session_id]
    session["history"].append({"role": "user", "content": message})
    
    prompt = build_prompt(session)
    response = await llm.complete(prompt, session["history"])
    
    session["history"].append({"role": "assistant", "content": response})
    session["turn"] += 1
    
    return {"response": response, "trust": session["trust"]}

# 3. End session
def end_session(session_id: str) -> dict:
    session = SESSIONS.pop(session_id)
    return summarize(session)
```

### Personas (Hardcoded Example)

```python
PERSONAS = {
    "coach_sarah": {
        "name": "Sarah",
        "core_identity": "Supportive former smoker who understands the struggle",
        "stage_of_change": "contemplation",
        "trust_baseline": 0.5,
        "voice": {"speed": 1.0, "tone": "warm"}
    },
    "dr_miller": {
        "name": "Dr. Miller",
        "core_identity": "Evidence-based medical professional",
        "stage_of_change": "preparation",
        "trust_baseline": 0.6,
        "voice": {"speed": 0.9, "tone": "professional"}
    }
}
```

### Trust Calculation (Simple)

```python
def calculate_trust(response: str, message: str) -> float:
    # Simple heuristics
    if any(word in response.lower() for word in ["understand", "hear you", "that sounds"]):
        return 0.02  # Empathy bonus
    if "?" in message and "?" in response:
        return 0.01  # Engagement bonus
    return 0.0
```

### Advantages

- **Zero infrastructure** - No database, no migrations
- **Instant startup** - No connection overhead
- **Simple debugging** - Full state in memory
- **Easy deployment** - Single file or minimal container

### Limitations

- Sessions lost on restart (unless persisted to file)
- No cross-session memory
- Limited context window (8-16k tokens typical)
- No user accounts/auth

### Scaling Path

When needed, add:
1. `history/` directory for file-based persistence
2. SQLite for simple persistence
3. Redis for session storage
4. Full database for production
