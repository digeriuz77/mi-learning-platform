# Chat Performance Analysis Functions

This document describes how the smoking-cessation app analyzes performance in chat conversations.

## Overview

The app uses a multi-layered analysis system to evaluate coaching interactions. Analysis occurs at three levels:

1. **Real-time interaction analysis** - Per-message assessment during conversation
2. **Session-level analytics** - Aggregate metrics and trust progression tracking
3. **Post-session comprehensive analysis** - Deep MAPS framework analysis with AI

---

## 1. Real-Time Interaction Analysis

### UnifiedInteractionAnalyzer (Primary)

**Location:** `src/services/unified_interaction_analyzer.py`

Single-call LLM analysis that evaluates all dimensions simultaneously, reducing LLM calls by 80%.

```python
class UnifiedInteractionAnalyzer:
    async def analyze_interaction(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> InteractionAnalysis
```

#### Analysis Dimensions

| Dimension | Values | Description |
|-----------|--------|-------------|
| `user_approach` | `collaborative`, `reflective`, `directive`, `questioning`, `neutral` | Communication style used |
| `empathy_tone` | `hostile`, `neutral`, `supportive`, `deeply_empathetic` | Emotional warmth level |
| `emotional_safety` | `true`, `false` | Whether client feels safe |
| `interaction_quality` | `poor`, `adequate`, `good`, `excellent` | Overall MI quality rating |
| `trust_trajectory` | `declining`, `stable`, `building`, `breakthrough` | Trust pattern over conversation |
| `mi_techniques_detected` | List[str] | MI techniques used (open_question, reflection, affirmation, etc.) |
| `mi_spirit_present` | `true`, `false` | Does message embody MI spirit? |
| `pressure_level` | `none`, `subtle`, `moderate`, `high` | Amount of pressure applied |
| `judgment_detected` | `true`, `false` | Contains judgment about client |
| `validation_present` | `true`, `false` | Acknowledges client's feelings |

#### Caching

Results are cached by message content to avoid redundant analysis:
```python
cache_key = f"{user_message}_{len(conversation_history or [])}"
```

---

### LLMInteractionAnalyzer (Legacy)

**Location:** `src/services/llm_interaction_analyzer.py`

Multi-call analyzer (5+ LLM calls per interaction). Maintained for backward compatibility.

```python
class LLMInteractionAnalyzer:
    async def assess_interaction_quality(
        self,
        user_message: str,
        conversation_history: List[Dict]
    ) -> InteractionContext
```

---

## 2. Session-Level Analytics

### AnalyticsService

**Location:** `src/services/analytics_service.py`

Tracks basic engagement and trust metrics throughout sessions.

#### SessionMetrics (Dataclass)

```python
@dataclass
class SessionMetrics:
    session_id: str
    persona_id: str
    start_time: datetime
    end_time: Optional[datetime]
    message_count: int
    user_messages: int
    persona_messages: int
    initial_trust_level: Optional[float]
    final_trust_level: Optional[float]
    peak_trust_level: Optional[float]
    trust_progression: List[float]  # Trust levels over time
    interaction_qualities: List[str]  # ['good', 'excellent', 'adequate']
    session_duration_minutes: float
    knowledge_tiers_unlocked: List[str]
```

#### Key Methods

| Method | Description |
|--------|-------------|
| `start_session(session_id, persona_id)` | Begin tracking a session |
| `add_message(role, trust_level, interaction_quality, knowledge_tier)` | Record each message |
| `end_session(session_id)` | Calculate final metrics |
| `get_session_stats(session_id)` | Get current statistics |
| `get_overall_stats(days=7)` | Aggregate stats over period |
| `get_trust_analysis(persona_id, days)` | Trust progression analysis |

#### Trust Analysis Output

```python
{
    'total_sessions_analyzed': 10,
    'trust_outcomes': {
        'improved': 7,      # Sessions where trust increased
        'declined': 2,      # Sessions where trust decreased
        'stable': 1         # Sessions where trust stayed same
    },
    'avg_trust_change': 0.15,
    'peak_trust_achieved': 0.85,
    'sessions_reaching_high_trust': 5  # Trust >= 0.8
}
```

---

## 3. Comprehensive MAPS Framework Analysis

### MAPSAnalysisService

**Location:** `src/services/analysis/maps_analysis_service.py`

Deep post-session analysis using the MAPS (Money and Pensions Service) person-centred coaching framework.

#### Three Core Dimensions

| Dimension | Score Range | Description |
|-----------|-------------|-------------|
| `foundational_trust_safety` | 1-5 | Psychological safety through authenticity and non-judgmental acceptance |
| `empathic_partnership_autonomy` | 1-5 | Deep empathic understanding while respecting autonomy |
| `empowerment_clarity` | 1-5 | Help client feel capable and clear about path forward |

#### Analysis Methods

| Method | Description |
|--------|-------------|
| `analyze_conversation_by_id(conversation_id)` | Analyze stored conversation |
| `analyze_transcript(transcript)` | Analyze raw transcript text |
| `_calculate_trust_metrics(messages)` | Extract trust progression from messages |
| `_find_high_impact_moments()` | Identify manager actions causing trust increases |
| `_find_trust_decreasing_moments()` | Identify problematic actions |
| `_analyze_technique_gaps()` | Identify unused MI techniques |
| `_analyze_persona_behavior_evolution()` | Track behavioral changes |

#### High-Impact Moment Detection

Trust changes are classified using LLM:

```python
# Trust increase moments (threshold: 0.08)
Techniques classified:
- Open Question
- Complex Reflection
- Simple Reflection
- Affirmation
- Summarization

# Trust decrease moments (threshold: 0.05)
Categories classified:
- Giving Advice (premature)
- Closed Question
- Directive Statement
- Confrontational
- Dismissive
- Interrupting
```

#### Behavioral Evolution Analysis

Tracks persona changes without exposing raw trust numbers:

| Metric | Description |
|--------|-------------|
| `response_length_change` | Words per response difference |
| `emotional_openness_change` | Emotional expression markers |
| `resistance_change` | Resistance indicators |
| `self_disclosure_change` | Personal disclosure frequency |

Evolution types: `significant_opening`, `slight_opening`, `remained_stable`, `increased_defensiveness`

#### MAPSAnalysisResult Structure

```python
{
    "core_coaching_effectiveness": {
        "foundational_trust_safety": {
            "score": 4,
            "evidence": ["example1", "example2"],
            "notes": "brief rationale"
        },
        "empathic_partnership_autonomy": {...},
        "empowerment_clarity": {...},
        "overall_score": 3.7,
        "summary": "overall summary"
    },
    "patterns_observed": {
        "manager_patterns": ["pattern1", "pattern2"],
        "employee_patterns": ["pattern1", "pattern2"],
        "interaction_dynamics": "description",
        "conversation_balance": {
            "manager_speaking_percentage": 50,
            "employee_speaking_percentage": 50
        }
    },
    "strengths_and_suggestions": {
        "strengths": [{"strength": "...", "example": "..."}],
        "opportunities": [{"area": "...", "suggestion": "..."}],
        "next_session_focus": ["focus1", "focus2"],
        "maps_alignment": "how conversation aligned with MAPS values"
    },
    "overall_quality_score": 7.5,
    "maps_values_summary": "paragraph about Transforming, Caring, Connecting"
}
```

---

## 4. Memory-Based Context Analysis

### MemoryScoringService

**Location:** `src/services/memory_scoring_service.py`

Retrieves relevant memories using weighted scoring for contextual analysis.

#### Scoring Weights

| Factor | Weight | Description |
|--------|--------|-------------|
| `relevance` | 60% | Keyword overlap + semantic similarity |
| `recency` | 25% | Exponential decay (half-life: 24 hours) |
| `importance` | 15% | Predefined memory importance |

#### Memory Sources

1. **Short-term memories** - Recent messages in current session
2. **Conversation summaries** - Session summaries with key topics
3. **Character knowledge** - Persona-specific background
4. **Long-term memories** - Persistent persona knowledge from database

#### Trust-Based Retrieval

Memory access is filtered by trust level:

| Trust Level | Max Importance | Description |
|-------------|----------------|-------------|
| < 0.4 (defensive) | 0.40 | Surface-level memories only |
| < 0.6 (cautious) | 0.70 | Medium depth memories |
| < 0.8 (opening) | 0.85 | Deeper memories |
| >= 0.8 (trusting) | 1.0 | All memories accessible |

---

## 5. MI Gamification & Progress Tracking

### MIGamificationService

**Location:** `src/services/mi_gamification_service.py`

Tracks skill development and awards badges based on technique usage.

#### Badge Criteria Types

| Criteria Type | Example | Description |
|---------------|---------|-------------|
| `technique_count` | `{"technique": "reflection", "count": 10, "in_session": true}` | Use technique N times |
| `streak` | `{"streak": 5, "quality_threshold": "good"}` | N consecutive quality interactions |
| `quality_percent` | `{"min_turns": 20, "quality_percent": 80, "quality_threshold": "good"}` | Quality percentage threshold |
| `empathy_tone` | `{"empathy_tone": "deeply_empathetic", "count": 5}` | Empathy level count |
| `collaborative_percent` | `{"collaborative_percent": 75}` | Percentage of collaborative approach |

#### Skill Progress Tracking

| Field | Description |
|-------|-------------|
| `technique_type` | MI technique name |
| `total_uses` | Total times technique used |
| `successful_uses` | Times technique received quality rating |
| `success_rate` | successful_uses / total_uses |
| `mastery_level` | `novice`, `developing`, `proficient`, `expert` |
| `improvement_trend` | `improving`, `stable`, `declining` |

#### MI Spirit Scores

Post-session aggregate metrics:

| Score | Description |
|-------|-------------|
| `avg_partnership` | Average partnership score |
| `avg_acceptance` | Average acceptance score |
| `avg_compassion` | Average compassion score |
| `avg_evocation` | Average evocation score |
| `overall_mi_spirit` | Weighted overall score |

---

## 6. API Endpoints

### Analysis Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analysis/text` | POST | Submit transcript for MAPS analysis |
| `/api/v1/analysis/status/{job_id}` | GET | Get analysis job status |
| `/api/v1/analysis/result/{job_id}` | GET | Get completed analysis |
| `/api/v1/maps/analyze/transcript` | POST | MAPS transcript analysis |
| `/api/v1/maps/analyze/conversation` | POST | MAPS conversation analysis |
| `/api/v1/maps/status/{job_id}` | GET | MAPS job status |
| `/api/v1/maps/result/{job_id}` | GET | MAPS results |

### MI Analytics Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/mi/session/{session_id}/finish` | POST | Complete session, award badges |
| `/api/mi/session/{session_id}/summary` | GET | Get session analytics |
| `/api/mi/dashboard` | GET | User dashboard with badges/progress |
| `/api/mi/technique-usage-graph` | GET | Technique usage over time |
| `/api/mi/mi-spirit-trends` | GET | MI spirit score trends |

---

## 7. Analysis Data Flow

```
User Message
    |
    v
+------------------------+
| UnifiedInteractionAnalyzer |  <-- Real-time per-message
| (single LLM call)           |
+------------------------+
    |
    v
InteractionContext:
- empathy_tone
- interaction_quality  
- emotional_safety
- user_approach
- trust_trajectory
- mi_techniques_detected
    |
    v
+------------------------+
|   AnalyticsService     |  <-- Session tracking
+------------------------+
    |
    v
SessionMetrics:
- message_count
- trust_progression
- interaction_qualities
    |
    v (on session end)
+------------------------+
| MIGamificationService  |  <-- Badges & progress
+------------------------+
    |
    v (optional async)
+------------------------+
|  MAPSAnalysisService   |  <-- Deep post-session
+------------------------+
    |
    v
MAPSAnalysisResult:
- core_coaching_effectiveness
- patterns_observed
- strengths_and_suggestions
- overall_quality_score
```

---

## 8. Database Tables

| Table | Purpose |
|-------|---------|
| `conversation_transcripts` | Message history with trust levels |
| `mi_technique_events` | Per-turn technique/quality tracking |
| `conversation_mi_summary` | Post-session MI analytics |
| `mi_skill_progress` | User skill development |
| `user_mi_badges` | Earned badges |
| `mi_badges` | Badge definitions |
| `long_term_memories` | Persistent persona knowledge |

---

## 9. Key Metrics Summary

### Real-Time Metrics
- Interaction quality per message
- Empathy tone per message
- Trust trajectory
- MI techniques detected

### Session Metrics
- Total messages
- Session duration
- Trust change (start to end)
- Peak trust achieved
- Interaction quality distribution

### Comprehensive Analysis
- MAPS overall quality score (1-10)
- Three dimension scores (1-5 each)
- Behavioral evolution type
- Technique gaps identified
- Strengths and opportunities
- Next session focus areas
