#!/usr/bin/env python
"""
MI Learning Platform Setup Script
Sets up the environment for local development with PostgreSQL
"""
import os
import sys
from pathlib import Path


def create_env_file():
    """Create .env file from template"""
    env_example = Path('.env.example')
    env_file = Path('.env')
    
    if env_file.exists():
        print(".env file already exists")
        return True
    
    if not env_example.exists():
        print("Error: .env.example not found")
        return False
    
    # Copy example to .env
    content = env_example.read_text()
    
    # Set default localhost values for development
    content = content.replace(
        'DB_PASSWORD=your_supabase_password',
        'DB_PASSWORD=postgres'
    )
    content = content.replace(
        'DB_HOST=your_project_id.supabase.co',
        'DB_HOST=localhost'
    )
    content = content.replace(
        'SUPABASE_URL=https://your_project_id.supabase.co',
        'SUPABASE_URL=http://localhost:8000'
    )
    content = content.replace(
        'SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key',
        'SUPABASE_SERVICE_ROLE_KEY=local_dev_key'
    )
    content = content.replace(
        'GROQ_API_KEY=your_groq_api_key',
        'GROQ_API_KEY='
    )
    
    env_file.write_text(content)
    print("Created .env file with localhost defaults")
    return True


def setup_local_database():
    """Setup instructions for local PostgreSQL"""
    print("\n=== Local Database Setup ===")
    print("To run locally, you need PostgreSQL installed:")
    print("1. Install PostgreSQL: https://www.postgresql.org/download/")
    print("2. Create a database:")
    print("   - Open pgAdmin or psql")
    print("   - Run: CREATE DATABASE mi_learning;")
    print("3. Update .env file with your PostgreSQL credentials")
    print("4. Run: python import_modules.py")
    print()


def run_django_migrations():
    """Run Django migrations for user auth"""
    print("\n=== Running Django Migrations ===")
    try:
        os.system('python manage.py migrate')
        print("Django migrations completed")
        return True
    except Exception as e:
        print(f"Error running migrations: {e}")
        return False


def import_mi_modules():
    """Import MI learning modules"""
    print("\n=== Importing MI Learning Modules ===")
    try:
        os.system('python import_modules.py')
        print("MI modules imported successfully")
        return True
    except Exception as e:
        print(f"Error importing modules: {e}")
        return False


def create_superuser():
    """Create Django superuser"""
    print("\n=== Creating Superuser ===")
    print("To create an admin user, run:")
    print("python manage.py createsuperuser")
    print()


def main():
    """Main setup process"""
    print("MI Learning Platform Setup")
    print("=" * 40)
    
    # Change to project directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Step 1: Create .env file
    if not create_env_file():
        sys.exit(1)
    
    # Step 2: Setup database instructions
    setup_local_database()
    
    # Step 3: Install dependencies
    print("\n=== Installing Dependencies ===")
    os.system('pip install -r requirements.txt')
    
    # Step 4: Run Django migrations
    if not run_django_migrations():
        print("Continuing without migrations...")
    
    # Step 5: Import MI modules (requires database)
    print("\nNote: The following steps require a running PostgreSQL database")
    user_input = input("Do you have PostgreSQL running? (y/n): ")
    if user_input.lower() == 'y':
        import_mi_modules()
    else:
        print("Skip module import. Run 'python import_modules.py' after database setup")
    
    # Step 6: Create superuser instructions
    create_superuser()
    
    print("\n=== Setup Complete ===")
    print("To start the development server:")
    print("python manage.py runserver")
    print("\nThe app will be available at: http://localhost:8000/game/")
    print("\nAdmin interface: http://localhost:8000/admin/")


if __name__ == '__main__':
    main()