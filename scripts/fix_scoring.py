#!/usr/bin/env python3
"""
Script to fix the scoring issue by:
1. Calculating max_points_available for all modules from dialogue structure
2. Updating completion_score based on points_earned / max_points_available
3. Fixing Gary's user_progress record specifically

Usage:
    python scripts/fix_scoring.py [--dry-run]
"""
import asyncio
import sys
import os
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client, Client
from dotenv import load_dotenv

# Import scoring service
from app.services.scoring_service import ScoringService


async def fix_scoring(supabase: Client, dry_run: bool = False):
    """Fix the scoring issue by updating max_points and completion scores."""
    
    print(f"{'[DRY RUN] ' if dry_run else ''}Starting scoring fix...")
    
    # Step 1: Get all modules
    print("\n1. Fetching all modules...")
    modules_response = supabase.table('learning_modules').select('id, title, dialogue_content').execute()
    modules = modules_response.data
    print(f"   Found {len(modules)} modules")
    
    # Step 2: Calculate max_points_available for each module
    print("\n2. Calculating max_points_available for each module...")
    module_max_points = {}
    
    for module in modules:
        module_id = module['id']
        dialogue_content = module.get('dialogue_content', {})
        
        # Calculate max points from dialogue
        max_points = ScoringService.calculate_max_points_available(dialogue_content)
        module_max_points[module_id] = max_points
        
        print(f"   Module '{module.get('title', module_id)}': {max_points} max points")
        
        if not dry_run:
            # Update the module with max_points_available
            supabase.table('learning_modules').update({
                'max_points_available': max_points
            }).eq('id', module_id).execute()
            print(f"     → Updated in database")
    
    # Step 3: Get all user progress records
    print("\n3. Fetching user progress records...")
    progress_response = supabase.table('user_progress').select('*').execute()
    progress_records = progress_response.data
    print(f"   Found {len(progress_records)} progress records")
    
    # Step 4: Update completion_score based on points_earned / max_points_available
    print("\n4. Updating completion scores...")
    
    updated_count = 0
    fixed_gary = False
    
    for progress in progress_records:
        user_id = progress['user_id']
        module_id = progress['module_id']
        points_earned = progress.get('points_earned', 0)
        old_score = progress.get('completion_score', 0)
        status = progress.get('status', 'in_progress')
        
        # Get max_points for this module
        max_points = module_max_points.get(module_id, 500)  # Default to 500 if not found
        
        # Calculate new completion score
        if max_points > 0 and status == 'completed':
            new_score = int((points_earned / max_points) * 100)
            new_score = min(max(new_score, 0), 100)  # Clamp between 0-100
        else:
            new_score = old_score
        
        # Check if this is Gary's record (the one with 1000 points at 55%)
        is_gary = user_id == "85e5eeba-9838-4a31-862d-84c8317e2be4"
        
        if new_score != old_score or is_gary:
            print(f"   User {user_id[:8]}... | Module {module_id[:8]}... | {old_score}% → {new_score}% | {points_earned} pts")
            
            if not dry_run:
                supabase.table('user_progress').update({
                    'completion_score': new_score
                }).eq('id', progress['id']).execute()
                
                if is_gary:
                    fixed_gary = True
            
            updated_count += 1
    
    print(f"\n   Updated {updated_count} records")
    
    if dry_run:
        print(f"\n[DRY RUN] No changes were made.")
    else:
        print(f"\n✓ Scoring fix complete!")
        
        if not fixed_gary:
            # Check specifically for Gary's record
            gary_progress = next(
                (p for p in progress_records 
                 if p['user_id'] == "85e5eeba-9838-4a31-862d-84c8317e2be4"),
                None
            )
            if gary_progress:
                print(f"\n⚠ Gary's record details:")
                print(f"   User ID: {gary_progress['user_id']}")
                print(f"   Module ID: {gary_progress['module_id']}")
                print(f"   Points earned: {gary_progress['points_earned']}")
                print(f"   Old score: {gary_progress['completion_score']}")
                module_max = module_max_points.get(gary_progress['module_id'], 500)
                print(f"   Max points: {module_max}")
                new_calc = int((gary_progress['points_earned'] / module_max) * 100)
                print(f"   New score: {new_calc}%")
    
    return module_max_points


async def verify_module_1_max_points():
    """Verify Module 1's max points calculation specifically."""
    print("\n" + "="*60)
    print("Verifying Module 1 max points calculation...")
    print("="*60)
    
    # Load module 1 JSON
    module_path = Path(__file__).parent.parent / 'mi_modules' / 'module_1.json'
    
    with open(module_path, 'r') as f:
        dialogue_content = json.load(f)['dialogue_tree']
    
    # Calculate max points
    max_points = ScoringService.calculate_max_points_available(dialogue_content)
    
    print(f"\nModule 1: {dialogue_content.get('title', 'Unknown')}")
    print(f"Max points calculated: {max_points}")
    print(f"\nBreakdown:")
    print(f"  - EXCELLENT_POINTS: {ScoringService.EXCELLENT_POINTS}")
    print(f"  - FIRST_ATTEMPT_BONUS: {ScoringService.FIRST_ATTEMPT_BONUS}")
    print(f"  - CHANGE_TALK_BONUS: {ScoringService.CHANGE_TALK_BONUS}")
    print(f"  - MODULE_COMPLETION_BONUS: {ScoringService.MODULE_COMPLETION_BONUS}")
    print(f"  - Max per node (excellent + bonuses): {ScoringService.EXCELLENT_POINTS + ScoringService.FIRST_ATTEMPT_BONUS + ScoringService.CHANGE_TALK_BONUS}")
    
    # Show path breakdown
    nodes = dialogue_content.get('nodes', [])
    print(f"\n  - Total nodes in dialogue: {len(nodes)}")
    
    # Estimate: ~5 nodes on best path × 250 points = ~1250 max
    estimated_max = 5 * (ScoringService.EXCELLENT_POINTS + ScoringService.FIRST_ATTEMPT_BONUS + ScoringService.CHANGE_TALK_BONUS)
    print(f"  - Estimated max (5 nodes × 250): ~{estimated_max}")
    
    return max_points


async def main():
    """Main entry point."""
    # Load environment
    load_dotenv()
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY (or SUPABASE_ANON_KEY) must be set in .env")
        sys.exit(1)
    
    # Create client
    supabase: Client = create_client(supabase_url, supabase_key)
    
    # Check for dry-run flag
    dry_run = '--dry-run' in sys.argv
    
    # Verify Module 1 calculation first
    await verify_module_1_max_points()
    
    # Run the fix
    await fix_scoring(supabase, dry_run=dry_run)


if __name__ == '__main__':
    asyncio.run(main())
