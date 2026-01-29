"""
Check Supabase tables via HTTP - using Railway deployed endpoint
"""
import urllib.request
import json

# The deployed app can check tables
API_URL = "https://mi-learning-platform.up.railway.app"

print("Checking Supabase tables via Railway API...")

try:
    # Check health
    req = urllib.request.Request(f"{API_URL}/health")
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode())
        print(f"[OK] App is running: {data}")

    # Try to get auth health
    req = urllib.request.Request(f"{API_URL}/api/v1/auth/health")
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode())
        print(f"[OK] Auth health: {data}")

    # Try test supabase endpoint
    req = urllib.request.Request(f"{API_URL}/api/v1/auth/test-supabase")
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode())
        print(f"[OK] Supabase test:")
        print(f"  Status: {data.get('status')}")
        print(f"  Message: {data.get('message')}")
        print(f"  Modules: {data.get('modules_count', 0)}")
        if 'config_present' in data:
            print(f"  Config: {data.get('config_present')}")

except urllib.error.HTTPError as e:
    print(f"[ERROR] HTTP Error {e.code}: {e.reason}")
    try:
        error_body = e.read().decode()
        print(f"  Details: {error_body}")
    except:
        pass
except Exception as e:
    print(f"[ERROR] Error: {e}")

print("\n" + "="*60)
print("If the app is healthy but auth/register fails with 500,")
print("the user_profiles table is likely missing.")
print("\nGo to Supabase Dashboard > SQL Editor and run:")
print("  docs/schema.sql")
print("="*60)
