"""
Import MI Learning Modules from JSON to Supabase
Following supabase-hello-world pattern

This script loads JSON module files and imports them into the
learning_modules table using the Supabase Python client.
"""
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local') or load_dotenv('.env')

# Import Supabase client
from supabase import create_client

# Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

# Verify environment
if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("=" * 60)
    print("ERROR: Missing Supabase credentials")
    print("=" * 60)
    print("Please set the following environment variables:")
    print("  - SUPABASE_URL")
    print("  - SUPABASE_SERVICE_ROLE_KEY")
    print()
    print("You can set them in .env.local or .env file")
    print("=" * 60)
    sys.exit(1)


def create_supabase_client():
    """Create Supabase admin client"""
    print(f"Connecting to Supabase: {SUPABASE_URL[:40]}...")
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    print("✓ Connected successfully")
    return client


def load_json_module(json_path):
    """Load a JSON module file"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def transform_json_to_db_format(json_data, module_number):
    """
    Transform JSON data to match learning_modules table schema.

    JSON structure:
    {
      "dialogue_tree": {
        "title": "...",
        "learning_objective": "...",
        "technique_focus": "...",
        "stage_of_change": "...",
        "mi_process": "...",
        "description": "...",
        "start_node": "node_1",
        "nodes": [...]
      }
    }

    DB structure (learning_modules table):
    {
      "module_number": int,
      "title": str,
      "slug": str,
      "learning_objective": str,
      "technique_focus": str,
      "stage_of_change": str,
      "description": str,
      "points": int,
      "dialogue_content": jsonb (entire dialogue_tree),
      "is_published": bool,
      "display_order": int
    }
    """
    dialogue_tree = json_data.get('dialogue_tree', {})

    # Create slug from title
    title = dialogue_tree.get('title', f'Module {module_number}')
    slug = title.lower().replace(':', '').replace(' ', '-').strip('-')

    # Build the database record
    return {
        'module_number': module_number,
        'title': title,
        'slug': slug,
        'learning_objective': dialogue_tree.get('learning_objective', ''),
        'technique_focus': dialogue_tree.get('technique_focus', ''),
        'stage_of_change': dialogue_tree.get('stage_of_change', ''),
        'description': dialogue_tree.get('description', ''),
        'points': 500,  # Default points per module
        'dialogue_content': dialogue_tree,  # Store entire dialogue_tree as JSONB
        'is_published': True,
        'display_order': module_number
    }


def import_module(client, json_path, module_number):
    """Import a single module from JSON file"""
    filename = json_path.name
    print(f"\n{'=' * 60}")
    print(f"Importing: {filename}")
    print('=' * 60)

    try:
        # Load JSON
        json_data = load_json_module(json_path)
        dialogue_tree = json_data.get('dialogue_tree', {})

        print(f"  Title: {dialogue_tree.get('title', 'Unknown')}")
        print(f"  Technique: {dialogue_tree.get('technique_focus', 'Unknown')}")
        print(f"  Stage: {dialogue_tree.get('stage_of_change', 'Unknown')}")
        node_count = len(dialogue_tree.get('nodes', []))
        print(f"  Nodes: {node_count}")

        # Transform to DB format
        module_data = transform_json_to_db_format(json_data, module_number)

        # Check if module already exists
        existing = client.table('learning_modules').select('id').eq('module_number', module_number).execute()

        if existing.data:
            # Update existing module
            module_id = existing.data[0]['id']
            print(f"  Updating existing module (ID: {module_id})...")

            client.table('learning_modules').update(module_data).eq('id', module_id).execute()
            print(f"  ✓ Module updated successfully")
        else:
            # Insert new module
            print(f"  Inserting new module...")
            response = client.table('learning_modules').insert(module_data).execute()

            if response.data:
                module_id = response.data[0]['id']
                print(f"  ✓ Module imported successfully (ID: {module_id})")
            else:
                print(f"  ✗ Failed to insert module")
                return False

        return True

    except Exception as e:
        print(f"  ✗ Error importing {filename}: {e}")
        import traceback
        traceback.print_exc()
        return False


def import_all_modules(client):
    """Import all modules from mi_modules directory"""
    modules_dir = Path(__file__).parent / 'mi_modules'

    if not modules_dir.exists():
        print(f"ERROR: Modules directory not found: {modules_dir}")
        return False

    # Find all JSON files
    json_files = sorted(modules_dir.glob('module_*.json'))
    print(f"\nFound {len(json_files)} JSON files in {modules_dir}")

    # Filter out duplicates (e.g., module_1.json and module_1_simple_reflections.json)
    seen_numbers = set()
    unique_files = []
    for json_file in json_files:
        # Extract module number from filename (module_1.json -> 1)
        import re
        match = re.search(r'module_(\d+)', json_file.name)
        if match:
            num = int(match.group(1))
            if num not in seen_numbers:
                seen_numbers.add(num)
                unique_files.append((num, json_file))

    print(f"Importing {len(unique_files)} unique modules...")

    # Import each module
    success_count = 0
    failed = []

    for module_number, json_file in unique_files:
        if import_module(client, json_file, module_number):
            success_count += 1
        else:
            failed.append(json_file.name)

    # Summary
    print(f"\n{'=' * 60}")
    print("IMPORT SUMMARY")
    print('=' * 60)
    print(f"Successfully imported: {success_count}/{len(unique_files)} modules")

    if failed:
        print(f"\nFailed to import:")
        for filename in failed:
            print(f"  - {filename}")

    return success_count == len(unique_files)


def verify_import(client):
    """Verify modules were imported correctly"""
    print(f"\n{'=' * 60}")
    print("VERIFYING IMPORT")
    print('=' * 60)

    response = client.table('learning_modules').select('id, module_number, title').order('module_number').execute()

    if response.data:
        print(f"\n✓ Found {len(response.data)} modules in database:")
        for module in response.data:
            print(f"  Module {module['module_number']}: {module['title']}")
        return True
    else:
        print("\n✗ No modules found in database")
        return False


def main():
    """Main import process"""
    print("=" * 60)
    print("MI Learning Platform - Module Import Tool")
    print("Supabase Python Client")
    print("=" * 60)

    # Create client
    try:
        client = create_supabase_client()
    except Exception as e:
        print(f"ERROR: Failed to connect to Supabase: {e}")
        sys.exit(1)

    # Import all modules
    success = import_all_modules(client)

    # Verify
    verify_import(client)

    # Final status
    print(f"\n{'=' * 60}")
    if success:
        print("✓ ALL MODULES IMPORTED SUCCESSFULLY")
        print()
        print("Next steps:")
        print("  1. Start the FastAPI server: uvicorn app.main:app --reload")
        print("  2. Test the API: http://localhost:8000/api/v1/modules")
        print("  3. View documentation: http://localhost:8000/docs")
    else:
        print("⚠ SOME MODULES FAILED TO IMPORT")
        print("Please review the errors above and try again.")
    print("=" * 60)

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
