#!/usr/bin/env python
"""Set max_points_available = 600 for all modules"""
import os
import json
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

print("Setting max_points_available = 600 for all modules...")

# Get all modules with id
result = supabase.table('learning_modules').select('id, module_number').execute()
print(f"Found {len(result.data)} modules")

# Update each one
for m in result.data:
    supabase.table('learning_modules').update({'max_points_available': 600}).eq('id', m['id']).execute()
    print(f"  Module {m['module_number']}: OK")

# Verify
print("\nVerifying:")
modules = supabase.table('learning_modules').select('module_number, max_points_available').execute()
for m in modules.data:
    print(f"  Module {m['module_number']}: {m['max_points_available']} pts")
