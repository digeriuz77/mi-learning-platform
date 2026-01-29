"""
Direct test of registration endpoint to see actual error
"""
import urllib.request
import json

API_URL = "https://mi-learning-platform.up.railway.app"

print("Testing registration endpoint directly...")
print("-" * 50)

test_data = {
    "email": "test@example.com",
    "password": "test123456",
    "display_name": "Test User"
}

try:
    req = urllib.request.Request(
        f"{API_URL}/api/v1/auth/register",
        data=json.dumps(test_data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )

    with urllib.request.urlopen(req, timeout=10) as response:
        print(f"Status: {response.status}")
        body = response.read().decode()
        print(f"Response: {body}")
        data = json.loads(body)
        print(f"\n[SUCCESS] Registration worked!")
        print(f"  User: {data.get('user', {}).get('email')}")
        print(f"  Token: {data.get('access_token', '')[:20]}...")

except urllib.error.HTTPError as e:
    print(f"\n[ERROR] HTTP {e.code}: {e.reason}")
    try:
        body = e.read().decode()
        print(f"Error body: {body}")
    except:
        pass

print("\n" + "=" * 50)
