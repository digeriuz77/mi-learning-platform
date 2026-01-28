#!/usr/bin/env python
"""
Simple Module Import Script using httpx instead of supabase package

Imports module content from mi_modules/*.json into Supabase database.
Run this after setting up your Supabase project and running the schema migration.

Usage:
    python scripts/import_modules_simple.py

Requirements:
    - SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env file
    - Supabase database schema already created
"""
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import httpx

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()


def import_module(client, table_name: str, module_number: int, file_path: str) -> dict:
    """
    Import a single module from JSON file to Supabase.

    Args:
        client: httpx client
        table_name: Supabase table name
        module_number: Module number (1-12)
        file_path: Path to module JSON file

    Returns:
        dict: Import result
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
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

        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')

        headers = {
            'apikey': supabase_key,
            'Authorization': f'Bearer {supabase_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }

        # Check if module already exists
        response = client.get(
            f'{supabase_url}/rest/v1/{table_name}',
            params={'module_number': f'eq.{module_number}', 'select': 'id'},
            headers=headers
        )

        if response.status_code == 200:
            existing = response.json()
            if existing:
                # Update existing module
                module_id = existing[0]['id']
                response = client.patch(
                    f'{supabase_url}/rest/v1/{table_name}',
                    params={'id': f'eq.{module_id}'},
                    json=module_data,
                    headers=headers
                )
                if response.status_code == 200:
                    return {
                        'status': 'updated',
                        'module_number': module_number,
                        'title': module_data['title'],
                        'id': module_id
                    }

        # Insert new module
        response = client.post(
            f'{supabase_url}/rest/v1/{table_name}',
            json=module_data,
            headers=headers
        )

        if response.status_code in [200, 201]:
            result = response.json()
            return {
                'status': 'created',
                'module_number': module_number,
                'title': module_data['title'],
                'id': result[0]['id'] if result else 'unknown'
            }
        else:
            return {
                'status': 'error',
                'module_number': module_number,
                'error': f'HTTP {response.status_code}: {response.text}'
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
        print("[ERROR] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env file")
        return 1

    # Create HTTP client
    print("[+] Connecting to Supabase...")
    client = httpx.Client(timeout=30.0)

    # Check connection
    try:
        headers = {
            'apikey': supabase_key,
            'Authorization': f'Bearer {supabase_key}',
        }
        response = client.get(
            f'{supabase_url}/rest/v1/learning_modules',
            params={'select': 'id', 'limit': '1'},
            headers=headers
        )
        if response.status_code in [200, 406]:
            print("[OK] Connected to Supabase")
        else:
            print(f"[ERROR] Error connecting to Supabase: HTTP {response.status_code}")
            return 1
    except Exception as e:
        print(f"[ERROR] Error connecting to Supabase: {e}")
        return 1

    # Import modules
    modules_dir = Path(__file__).parent.parent / 'mi_modules'
    results = []

    print(f"\n[*] Importing modules from {modules_dir}...\n")

    for i in range(1, 13):
        module_file = modules_dir / f'module_{i}.json'

        if module_file.exists():
            print(f"  -> Module {i}...", end=' ')
            result = import_module(client, 'learning_modules', i, str(module_file))
            results.append(result)

            if result['status'] == 'error':
                print(f"[X] Error: {result.get('error')}")
            else:
                status_icon = '[+]' if result['status'] == 'created' else '[*]'
                print(f"{status_icon} {result['status']}: {result.get('title', 'N/A')}")
        else:
            print(f"  -> Module {i}... [X] File not found: {module_file}")
            results.append({
                'status': 'error',
                'module_number': i,
                'error': f'File not found: {module_file}'
            })

    client.close()

    # Summary
    print("\n" + "="*50)
    created = sum(1 for r in results if r['status'] == 'created')
    updated = sum(1 for r in results if r['status'] == 'updated')
    errors = sum(1 for r in results if r['status'] == 'error')

    print(f"[*] Import Summary:")
    print(f"  Created: {created}")
    print(f"  Updated: {updated}")
    print(f"  Errors:  {errors}")

    if errors > 0:
        print("\n[!] Some modules failed to import")
        return 1
    else:
        print("\n[OK] All modules imported successfully!")
        return 0


if __name__ == '__main__':
    sys.exit(main())
