#!/usr/bin/env python
"""Update Module 1 max_points_available to 1000 based on Gary's perfect score."""
import os
import json
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

print("Updating Module 1 max_points_available to 1000...")

try:
    result = supabase.table('learning_modules').update({'max_points_available': 1000}).eq('module_number', 1).execute()
    print("Update result:", json.dumps(result.data, indent=2))
except Exception as e:
    print(f"Error: {e}")

print("\nVerifying update...")
try:
    module = supabase.table('learning_modules').select('module_number, title, max_points_available').eq('module_number', 1).execute()
    print(json.dumps(module.data, indent=2))
except Exception as e:
    print(f"Error reading: {e}")
