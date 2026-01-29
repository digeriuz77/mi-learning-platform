"""
Code Structure Verification

Verifies that all files are properly structured for Railway deployment.
This script doesn't require dependencies to be installed.
"""
import ast
import sys
import os
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


def verify_file_syntax(filepath):
    """Verify Python file has valid syntax"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            ast.parse(f.read())
        return True, "OK"
    except SyntaxError as e:
        return False, f"Syntax error: {e}"


def verify_imports(filepath, required_imports):
    """Verify file contains required imports"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    missing = []
    for imp in required_imports:
        if imp not in content:
            missing.append(imp)

    return len(missing) == 0, missing


def main():
    print("=" * 60)
    print("Code Structure Verification")
    print("MI Learning Platform - Railway Deployment")
    print("=" * 60)
    print()

    files_to_check = {
        "app/core/supabase.py": {
            "imports": ["from supabase import", "create_client", "Client"],
            "description": "Supabase client module"
        },
        "app/api/v1/auth.py": {
            "imports": ["from fastapi import", "from supabase import", "get_supabase"],
            "description": "Auth endpoints"
        },
        "app/config.py": {
            "imports": ["from pydantic_settings import", "BaseSettings"],
            "description": "Configuration module"
        },
        "app/main.py": {
            "imports": ["from fastapi import FastAPI", "from app.config import settings"],
            "description": "Main application"
        },
    }

    all_ok = True

    for filepath, checks in files_to_check.items():
        path = Path(filepath)

        print(f"Checking: {filepath}")
        print(f"  Description: {checks['description']}")

        if not path.exists():
            print(f"  ❌ File not found")
            all_ok = False
            continue

        # Check syntax
        syntax_ok, msg = verify_file_syntax(path)
        if not syntax_ok:
            print(f"  ❌ {msg}")
            all_ok = False
            continue
        else:
            print(f"  ✓ Syntax OK")

        # Check imports
        imports_ok, missing = verify_imports(path, checks['imports'])
        if not imports_ok:
            print(f"  ⚠ Missing imports: {missing}")
        else:
            print(f"  ✓ Required imports present")

        print()

    # Check Dockerfile
    dockerfile_path = Path("Dockerfile")
    print("Checking: Dockerfile")
    if dockerfile_path.exists():
        content = dockerfile_path.read_text()
        if "FROM python:" in content:
            print("  ✓ Python base image found")
        if "uvicorn" in content:
            print("  ✓ Uvicorn command found")
        if "EXPOSE" in content:
            print("  ✓ Port expose directive found")
        if "HEALTHCHECK" in content:
            print("  ✓ Health check configured")
    else:
        print("  ❌ Dockerfile not found")
        all_ok = False

    print()

    # Check requirements.txt
    req_path = Path("requirements.txt")
    print("Checking: requirements.txt")
    if req_path.exists():
        content = req_path.read_text()
        required = ["fastapi", "supabase", "pydantic", "uvicorn"]
        for pkg in required:
            if pkg in content.lower():
                print(f"  ✓ {pkg} listed")
            else:
                print(f"  ❌ {pkg} missing")
                all_ok = False
    else:
        print("  ❌ requirements.txt not found")
        all_ok = False

    print()
    print("=" * 60)

    if all_ok:
        print("✅ All code structure checks passed!")
        print()
        print("The code is ready for Railway deployment.")
        print()
        print("Next steps:")
        print("  1. Set environment variables in Railway dashboard:")
        print("     - SUPABASE_URL")
        print("     - SUPABASE_KEY")
        print("     - SUPABASE_SERVICE_ROLE_KEY")
        print("     - SUPABASE_JWT_SECRET")
        print()
        print("  2. Run database schema in Supabase:")
        print("     - Copy supabase_schema.sql")
        print("     - Paste in Supabase SQL Editor")
        print("     - Execute to create tables")
        print()
        print("  3. Deploy to Railway:")
        print("     - Connect your GitHub repo")
        print("     - Railway will auto-deploy")
        print()
        print("  4. Test endpoints:")
        print("     - GET  /health")
        print("     - GET  /api/v1/auth/test-supabase")
        print("     - POST /api/v1/auth/register")
        print("     - POST /api/v1/auth/login")
        print()
    else:
        print("❌ Some checks failed. Please review the issues above.")
        print()

    return all_ok


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
