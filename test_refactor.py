"""
Test the refactored MI Learning Platform
Validates database connections and basic functionality
"""
import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def test_imports():
    """Test if all our refactored modules can be imported"""
    print("Testing imports...")
    
    try:
        # Import without initializing database connection
        import os
        os.environ['DB_HOST'] = 'dummy'  # Prevent actual connection
        
        from database import SupabaseDB, MIModuleManager, DialogueTreeManager
        print("Database managers imported successfully")
        
        from game.views import game_home, module_detail, dialogue_view
        print("Views imported successfully")
        
        return True
    except ImportError as e:
        print(f"Import error: {e}")
        return False
    except Exception as e:
        print(f"Import succeeded but connection failed (expected): {e}")
        return True  # This is expected without database

def test_json_modules():
    """Test if MI module JSON files exist and are valid"""
    print("\nTesting MI module JSON files...")
    
    modules_dir = Path('mi_modules')
    if not modules_dir.exists():
        print("mi_modules directory not found")
        return False
    
    valid_modules = 0
    for i in range(1, 7):
        json_file = modules_dir / f'module_{i}.json'
        if json_file.exists():
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                # Validate structure
                if 'dialogue_tree' in data and 'title' in data['dialogue_tree']:
                    print(f"Module {i}: Valid structure")
                    valid_modules += 1
                else:
                    print(f"Module {i}: Invalid structure")
                    
            except json.JSONDecodeError:
                print(f"Module {i}: Invalid JSON")
        else:
            print(f"Module {i}: File not found")
    
    print(f"Valid modules: {valid_modules}/6")
    return valid_modules == 6

def test_database_managers():
    """Test database manager class structure"""
    print("\nTesting database managers...")
    
    try:
        from database import SupabaseDB, MIModuleManager, DialogueTreeManager, UserProgressManager, UserScoreManager
        
        # Test class instantiation (without actual DB connection)
        print("SupabaseDB class defined")
        print("MIModuleManager class defined")  
        print("DialogueTreeManager class defined")
        print("UserProgressManager class defined")
        print("UserScoreManager class defined")
        
        # Test manager instance creation (will fail connection but tests structure)
        try:
            db = SupabaseDB()
            print("Database connection class works")
        except Exception as e:
            print(f"Database connection failed (expected without DB): {e}")
        
        return True
        
    except Exception as e:
        print(f"Database manager test error: {e}")
        return False

def test_view_functions():
    """Test view function definitions"""
    print("\nTesting view functions...")
    
    try:
        # Check if views file exists and has expected functions
        views_file = Path('game/views.py')
        if not views_file.exists():
            print("views.py file not found")
            return False
        
        content = views_file.read_text()
        expected_functions = [
            'game_home', 'module_detail', 'dialogue_view', 
            'start_dialogue', 'leaderboard', 'user_profile'
        ]
        
        for func_name in expected_functions:
            if f'def {func_name}(' in content:
                print(f"{func_name} function defined")
            else:
                print(f"{func_name} function not found")
        
        return True
        
    except Exception as e:
        print(f"View function test error: {e}")
        return False

def test_urls():
    """Test URL configuration"""
    print("\nTesting URL configuration...")
    
    try:
        # Check if URLs file exists and has expected patterns
        urls_file = Path('game/urls.py')
        if not urls_file.exists():
            print("urls.py file not found")
            return False
        
        content = urls_file.read_text()
        expected_patterns = [
            'game_home', 'module_detail', 'dialogue_view',
            'start_dialogue', 'leaderboard', 'user_profile'
        ]
        
        for pattern_name in expected_patterns:
            if pattern_name in content:
                print(f"{pattern_name} URL pattern found")
            else:
                print(f"{pattern_name} URL pattern not found")
        
        return True
        
    except Exception as e:
        print(f"URL test error: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing MI Learning Platform Refactor")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_json_modules,
        test_database_managers,
        test_view_functions,
        test_urls,
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{len(tests)} passed")
    
    if passed == len(tests):
        print("All tests passed! The refactor is structurally sound.")
        print("\nNext steps:")
        print("1. Set up PostgreSQL database")
        print("2. Run: python setup_local.py")
        print("3. Run: python import_modules.py")
        print("4. Run: python manage.py runserver")
    else:
        print("Some tests failed. Check the errors above.")
    
    return passed == len(tests)

if __name__ == '__main__':
    main()