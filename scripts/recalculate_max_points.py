#!/usr/bin/env python
"""
Recalculate max_points_available for all modules using the simplified scoring.

Points per choice (NO bonuses):
- Excellent: 150
- Good: 100
- Acceptable: 50
- Poor: 0

The max is the optimal path through the dialogue.
"""

import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client
from app.services.scoring_service import ScoringService

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

print("Recalculating max_points_available for all modules...")
print("Scoring: Excellent=150, Good=100, Acceptable=50, Poor=0 (NO bonuses)")

# Get all modules
result = (
    supabase.table("learning_modules")
    .select("id, module_number, title, dialogue_content, max_points_available")
    .execute()
)
print(f"Found {len(result.data)} modules\n")

updated_count = 0
for m in result.data:
    dialogue_content = m.get("dialogue_content")

    if dialogue_content:
        # Calculate using ScoringService
        new_max = ScoringService.calculate_max_points_available(dialogue_content)
        old_max = m.get("max_points_available")

        if new_max != old_max:
            supabase.table("learning_modules").update({"max_points_available": new_max}).eq("id", m["id"]).execute()
            print(f"  Module {m['module_number']}: {old_max} -> {new_max} pts (UPDATED)")
            updated_count += 1
        else:
            print(f"  Module {m['module_number']}: {new_max} pts (no change)")
    else:
        print(f"  Module {m['module_number']}: No dialogue content")

print(f"\nDone! Updated {updated_count} modules.")
