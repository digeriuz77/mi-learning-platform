"""
Supabase Hello World Test

Tests the Supabase connection following the supabase-hello-world pattern.
Run this to verify your Supabase setup is working correctly.
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Load environment variables
from dotenv import load_dotenv
# Try to load from .env, .env.local, or .env.example
loaded = load_dotenv('.env.local') or load_dotenv('.env') or load_dotenv('.env.example')
if not loaded:
    print("Warning: No .env file found. Using environment variables if available.")

# Now import after environment is loaded
from app.core.supabase import get_supabase, get_supabase_admin, test_connection
from app.config import settings


def test_config():
    """Test 1: Verify configuration is loaded"""
    print("=" * 60)
    print("TEST 1: Configuration Check")
    print("=" * 60)

    checks = {
        "SUPABASE_URL": settings.SUPABASE_URL,
        "SUPABASE_KEY": settings.SUPABASE_KEY,
        "SUPABASE_SERVICE_ROLE_KEY": settings.SUPABASE_SERVICE_ROLE_KEY,
        "SUPABASE_JWT_SECRET": settings.SUPABASE_JWT_SECRET,
    }

    all_present = True
    for key, value in checks.items():
        present = bool(value)
        status = "✓" if present else "✗"
        print(f"{status} {key}: {'Present' if present else 'Missing'}")
        if not present:
            all_present = False

    print()
    if not all_present:
        print("❌ Configuration incomplete. Please set all required environment variables.")
        print("   See .env.example for the required variables.")
        return False

    print("✅ All configuration variables present")
    print()
    return True


async def test_supabase_client():
    """Test 2: Initialize Supabase client"""
    print("=" * 60)
    print("TEST 2: Supabase Client Initialization")
    print("=" * 60)

    try:
        client = get_supabase()
        print("✅ Supabase client initialized successfully")
        print(f"   URL: {settings.SUPABASE_URL[:40]}...")
        print()
        return True
    except Exception as e:
        print(f"❌ Failed to initialize Supabase client: {e}")
        print()
        return False


async def test_table_access():
    """Test 3: Access Supabase tables"""
    print("=" * 60)
    print("TEST 3: Table Access")
    print("=" * 60)

    try:
        client = get_supabase()

        # Test mi_module table access
        print("Testing mi_module table access...")
        response = client.table('mi_module').select('id, title').limit(5).execute()

        if response.data is not None:
            print(f"✅ Successfully queried mi_module table")
            print(f"   Found {len(response.data)} modules")
            for module in response.data[:3]:
                print(f"   - {module.get('title', 'Unknown')}")
        else:
            print("⚠️  Query returned no data (table may be empty - this is OK)")
        print()
        return True

    except Exception as e:
        print(f"❌ Failed to access tables: {e}")
        print()
        print("Possible issues:")
        print("  1. Tables don't exist - run the schema migration")
        print("  2. RLS policies blocking access - check Supabase dashboard")
        print("  3. Invalid credentials - verify SUPABASE_KEY")
        print()
        return False


async def test_connection_endpoint():
    """Test 4: Connection test endpoint"""
    print("=" * 60)
    print("TEST 4: Connection Test Endpoint")
    print("=" * 60)

    try:
        result = await test_connection()

        if result.get("status") == "success":
            print("✅ Connection test endpoint successful")
            print(f"   Status: {result['status']}")
            print(f"   Message: {result['message']}")
            print()
            return True
        else:
            print("⚠️  Connection test returned error status")
            print(f"   Error: {result.get('message')}")
            print()
            return False

    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        print()
        return False


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Supabase Hello World Test")
    print("MI Learning Platform")
    print("=" * 60)
    print()

    # Test 1: Configuration
    if not test_config():
        return False

    # Test 2: Client init
    if not await test_supabase_client():
        return False

    # Test 3: Table access
    await test_table_access()

    # Test 4: Connection endpoint
    await test_connection_endpoint()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print()
    print("✅ Your Supabase connection is working!")
    print()
    print("Next steps:")
    print("  1. Start the FastAPI server: uvicorn app.main:app --reload")
    print("  2. Visit http://localhost:8000/docs for API documentation")
    print("  3. Test auth endpoints:")
    print("     - POST /api/v1/auth/register")
    print("     - POST /api/v1/auth/login")
    print("     - GET  /api/v1/auth/test-supabase")
    print()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
