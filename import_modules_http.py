"""
Import MI Learning Modules to Supabase using HTTP requests
No external dependencies required - uses Python standard library only
"""
import os
import sys
import json
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
import codecs

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


# Supabase configuration
SUPABASE_URL = "https://czcfscusbofyefrawkxc.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN6Y2ZzY3VzYm9meWVmcmF3a3hjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTY0MjAxMiwiZXhwIjoyMDg1MjE4MDEyfQ.HTfrn567UbRIfC7ufrSbcx6TiUHyt3iWf19HKQ6k12c"


def make_supabase_request(endpoint, method="GET", data=None, params=None):
    """Make an HTTP request to Supabase REST API"""
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"

    # Add query parameters if provided
    if params:
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        url = f"{url}?{query_string}"

    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    body = None
    if data:
        body = json.dumps(data).encode('utf-8')

    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as response:
            response_body = response.read().decode('utf-8')
            if response_body:
                return json.loads(response_body)
            return {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"  HTTP Error {e.code}: {error_body}")
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None


def load_json_module(json_path):
    """Load a JSON module file"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def sanitize_string(s):
    """Sanitize string for JSON"""
    if not s:
        return ""
    return str(s).replace('\\', '\\\\').replace('"', '\\"')


def import_module(module_number, json_path):
    """Import a single module from JSON file"""
    filename = os.path.basename(json_path)
    print(f"\n{'=' * 60}")
    print(f"Importing: {filename}")
    print('=' * 60)

    try:
        # Load JSON
        json_data = load_json_module(json_path)
        dialogue_tree = json_data.get('dialogue_tree', {})

        title = dialogue_tree.get('title', f'Module {module_number}')
        learning_objective = dialogue_tree.get('learning_objective', '')
        technique_focus = dialogue_tree.get('technique_focus', '')
        stage_of_change = dialogue_tree.get('stage_of_change', '')
        description = dialogue_tree.get('description', '')

        print(f"  Title: {title}")
        print(f"  Technique: {technique_focus}")
        print(f"  Stage: {stage_of_change}")
        node_count = len(dialogue_tree.get('nodes', []))
        print(f"  Nodes: {node_count}")

        # Create slug from title
        slug = title.lower().replace(':', '').replace(' ', '-').strip('-')
        slug = ''.join(c if c.isalnum() or c == '-' else '' for c in slug)

        # Check if module already exists
        existing = make_supabase_request(
            'learning_modules',
            params={'module_number': f'eq.{module_number}', 'select': 'id'}
        )

        module_data = {
            'module_number': module_number,
            'title': title,
            'slug': slug,
            'learning_objective': learning_objective,
            'technique_focus': technique_focus,
            'stage_of_change': stage_of_change,
            'description': description,
            'points': 500,
            'dialogue_content': dialogue_tree,
            'is_published': True,
            'display_order': module_number
        }

        if existing and len(existing) > 0:
            # Update existing module
            module_id = existing[0]['id']
            print(f"  Updating existing module (ID: {module_id})...")

            result = make_supabase_request(
                f'learning_modules?id=eq.{module_id}',
                method='PATCH',
                data=module_data
            )

            if result is not None:
                print(f"  ✓ Module updated successfully")
                return True
            else:
                print(f"  ✗ Failed to update module")
                return False
        else:
            # Insert new module
            print(f"  Inserting new module...")

            result = make_supabase_request(
                'learning_modules',
                method='POST',
                data=module_data
            )

            if result:
                print(f"  ✓ Module imported successfully")
                return True
            else:
                print(f"  ✗ Failed to insert module")
                return False

    except Exception as e:
        print(f"  ✗ Error importing {filename}: {e}")
        import traceback
        traceback.print_exc()
        return False


def import_all_modules():
    """Import all modules from mi_modules directory"""
    modules_dir = Path(__file__).parent / 'mi_modules'

    if not modules_dir.exists():
        print(f"ERROR: Modules directory not found: {modules_dir}")
        return False

    print(f"Modules directory: {modules_dir}")

    # Import modules 1-12
    success_count = 0
    failed = []

    for module_num in range(1, 13):
        json_file = modules_dir / f'module_{module_num}.json'

        if json_file.exists():
            if import_module(module_num, json_file):
                success_count += 1
            else:
                failed.append(json_file.name)
        else:
            print(f"\n⚠ Module {module_num} file not found: {json_file}")

    # Summary
    print(f"\n{'=' * 60}")
    print("IMPORT SUMMARY")
    print('=' * 60)
    print(f"Successfully imported: {success_count}/12 modules")

    if failed:
        print(f"\nFailed to import:")
        for filename in failed:
            print(f"  - {filename}")

    return success_count > 0


def verify_import():
    """Verify modules were imported correctly"""
    print(f"\n{'=' * 60}")
    print("VERIFYING IMPORT")
    print('=' * 60)

    response = make_supabase_request(
        'learning_modules',
        params={'select': 'id,module_number,title', 'order': 'module_number'}
    )

    if response:
        print(f"\n✓ Found {len(response)} modules in database:")
        for module in response:
            print(f"  Module {module['module_number']}: {module['title']}")
        return True
    else:
        print("\n✗ No modules found in database")
        return False


def main():
    """Main import process"""
    print("=" * 60)
    print("MI Learning Platform - Module Import Tool")
    print("Using Supabase REST API (no dependencies required)")
    print("=" * 60)
    print(f"Supabase URL: {SUPABASE_URL[:40]}...")
    print()

    # Import all modules
    success = import_all_modules()

    # Verify
    verify_import()

    # Final status
    print(f"\n{'=' * 60}")
    if success:
        print("✓ MODULES IMPORTED SUCCESSFULLY")
        print()
        print("Next steps:")
        print("  1. Start the FastAPI server:")
        print("     uvicorn app.main:app --reload")
        print("  2. Test the API:")
        print("     curl http://localhost:8000/api/v1/modules")
        print("  3. View documentation:")
        print("     http://localhost:8000/docs")
    else:
        print("⚠ IMPORT FAILED")
        print("Please check the errors above.")
    print("=" * 60)

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
