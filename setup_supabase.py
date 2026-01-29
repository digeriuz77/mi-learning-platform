"""
Setup Supabase tables for MI Learning Platform
Run this with your Supabase credentials to check/create tables
"""
import json
import urllib.request
import urllib.parse
import sys

# You'll need to input these
print("=" * 60)
print("MI Learning Platform - Supabase Setup")
print("=" * 60)
print("\nEnter your Supabase credentials (from https://supabase.com/dashboard/project/_/settings/api):")
print()

SUPABASE_URL = input("Supabase URL (e.g., https://xyz.supabase.co): ").strip()
SERVICE_KEY = input("Service Role Key (secret): ").strip()

if not SUPABASE_URL or not SERVICE_KEY:
    print("\n❌ Credentials required!")
    sys.exit(1)

print(f"\n🔍 Checking Supabase: {SUPABASE_URL}")

# Headers for admin requests
headers = {
    'apikey': SERVICE_KEY,
    'Authorization': f'Bearer {SERVICE_KEY}',
    'Content-Type': 'application/json'
}

# Tables we need
TABLES = [
    'user_profiles',
    'learning_modules',
    'user_progress',
    'dialogue_attempts'
]

# Check if tables exist
print("\n📋 Checking tables...")
for table in TABLES:
    try:
        url = f"{SUPABASE_URL}/rest/v1/{table}?select=*&limit=1"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                print(f"  ✓ {table} exists")
            else:
                print(f"  ✗ {table} - status {response.status}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"  ✗ {table} - NOT FOUND (needs to be created)")
        else:
            print(f"  ✗ {table} - error: {e.code}")
    except Exception as e:
        print(f"  ✗ {table} - error: {e}")

print("\n" + "=" * 60)
print("IMPORTANT: If any tables are missing, you need to create them.")
print("Go to Supabase SQL Editor and run the SQL from docs/schema.sql")
print("=" * 60)
