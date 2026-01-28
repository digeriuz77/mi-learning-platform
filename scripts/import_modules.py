#!/usr/bin/env python
"""
Module Data Import Script

Imports module content from mi_modules/*.json into Supabase database.
Run this after setting up your Supabase project and running the schema migration.

Usage:
    python scripts/import_modules.py

Requirements:
    - SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env file
    - Supabase database schema already created
"""
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client

# Load environment variables
load_dotenv()


def import_module(supabase, module_number: int, file_path: str) -> dict:
    """
    Import a single module from JSON file to Supabase.

    Args:
        supabase: Supabase admin client
        module_number: Module number (1-6)
        file_path: Path to module JSON file

    Returns:
        dict: Import result
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        dialogue_tree = data.get('dialogue_tree', data)

        # Extract metadata
        module_data = {
            "module_number": module_number,
            "title": dialogue_tree.get('title', f'Module {module_number}'),
            "slug": f"module-{module_number}",
            "learning_objective": dialogue_tree.get('learning_objective', ''),
            "technique_focus": dialogue_tree.get('technique_focus', ''),
            "stage_of_change": dialogue_tree.get('stage_of_change', ''),
            "mi_process": dialogue_tree.get('mi_process', ''),
            "description": dialogue_tree.get('description', ''),
            "dialogue_content": dialogue_tree,
            "points": 500,
            "display_order": module_number,
            "is_published": True
        }

        # Check if module already exists
        existing = supabase.table('learning_modules').select('*').eq('module_number', module_number).execute()

        if existing.data:
            # Update existing module
            result = supabase.table('learning_modules').update(module_data).eq('module_number', module_number).execute()
            return {
                'status': 'updated',
                'module_number': module_number,
                'title': module_data['title'],
                'id': result.data[0]['id']
            }
        else:
            # Insert new module
            result = supabase.table('learning_modules').insert(module_data).execute()
            return {
                'status': 'created',
                'module_number': module_number,
                'title': module_data['title'],
                'id': result.data[0]['id']
            }

    except Exception as e:
        return {
            'status': 'error',
            'module_number': module_number,
            'error': str(e)
        }


def main():
    """Main import function"""
    # Validate environment
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')

    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env file")
        return 1

    # Create Supabase client
    print(f"🔌 Connecting to Supabase...")
    supabase = create_client(supabase_url, supabase_key)

    # Check connection
    try:
        result = supabase.table('learning_modules').select('id').limit(1).execute()
        print("✅ Connected to Supabase")
    except Exception as e:
        print(f"❌ Error connecting to Supabase: {e}")
        print("\nMake sure you have:")
        print("1. Created a Supabase project")
        print("2. Run the schema migration (app/db/migrations/001_init_schema.sql)")
        return 1

    # Import modules
    modules_dir = Path(__file__).parent.parent / 'mi_modules'
    results = []

    print(f"\n📦 Importing modules from {modules_dir}...\n")

    for i in range(1, 13):
        module_file = modules_dir / f'module_{i}.json'

        if module_file.exists():
            print(f"  → Module {i}...", end=' ')
            result = import_module(supabase, i, str(module_file))
            results.append(result)

            if result['status'] == 'error':
                print(f"❌ Error: {result.get('error')}")
            else:
                status_icon = '✓' if result['status'] == 'created' else '↻'
                print(f"{status_icon} {result['status']}: {result.get('title', 'N/A')}")
        else:
            print(f"  → Module {i}... ❌ File not found: {module_file}")
            results.append({
                'status': 'error',
                'module_number': i,
                'error': f'File not found: {module_file}'
            })

    # Summary
    print("\n" + "="*50)
    created = sum(1 for r in results if r['status'] == 'created')
    updated = sum(1 for r in results if r['status'] == 'updated')
    errors = sum(1 for r in r['status'] == 'error' for r in results)

    print(f"📊 Import Summary:")
    print(f"  Created: {created}")
    print(f"  Updated: {updated}")
    print(f"  Errors:  {errors}")

    if errors > 0:
        print("\n❌ Some modules failed to import")
        return 1
    else:
        print("\n✅ All modules imported successfully!")
        return 0


if __name__ == '__main__':
    sys.exit(main())
