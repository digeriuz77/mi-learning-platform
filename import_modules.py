"""
Import MI Learning Modules from JSON to Supabase PostgreSQL
This script replaces the Django management command
"""
import os
import json
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from database import db, module_manager, dialogue_manager


def import_module_from_json(json_file_path, module_number):
    """Import a single module from JSON file"""
    
    print(f"Importing Module {module_number} from {json_file_path}")
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        dialogue_tree_data = data['dialogue_tree']
        
        # Create the module
        module_query = """
        INSERT INTO mi_module (
            module_number, title, description, learning_objective,
            technique_focus, stage_of_change, mi_process, difficulty,
            points, order_index
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        
        module_id = db.execute_insert(module_query, (
            module_number,
            dialogue_tree_data['title'],
            dialogue_tree_data.get('description', ''),
            dialogue_tree_data['learning_objective'],
            dialogue_tree_data['technique_focus'],
            dialogue_tree_data['stage_of_change'],
            dialogue_tree_data['mi_process'],
            'beginner',  # Default difficulty
            100,  # Default points
            module_number  # Order by module number
        ))
        
        print(f"Created module {module_id}")
        
        # Create dialogue tree
        tree_query = """
        INSERT INTO dialogue_tree (
            module_id, title, learning_objective, technique_focus,
            stage_of_change, mi_process, description, start_node_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        
        tree_id = db.execute_insert(tree_query, (
            module_id,
            dialogue_tree_data['title'],
            dialogue_tree_data['learning_objective'],
            dialogue_tree_data['technique_focus'],
            dialogue_tree_data['stage_of_change'],
            dialogue_tree_data['mi_process'],
            dialogue_tree_data.get('description', ''),
            dialogue_tree_data['start_node']
        ))
        
        print(f"Created dialogue tree {tree_id}")
        
        # Create nodes and choices
        for i, node_data in enumerate(dialogue_tree_data['nodes']):
            # Create dialogue node
            node_query = """
            INSERT INTO dialogue_node (
                tree_id, node_id, patient_statement, patient_context,
                change_talk_present, change_talk_type, is_ending,
                outcome, learning_summary, order_index
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """
            
            node_id = db.execute_insert(node_query, (
                tree_id,
                node_data['id'],
                node_data['patient_statement'],
                node_data.get('patient_context', ''),
                node_data.get('change_talk_present', False),
                node_data.get('change_talk_type', ''),
                node_data.get('is_ending', False),
                node_data.get('outcome', ''),
                node_data.get('learning_summary', ''),
                i
            ))
            
            print(f"Created node {node_data['id']} with ID {node_id}")
            
            # Create practitioner choices
            for j, choice_data in enumerate(node_data['practitioner_choices']):
                choice_query = """
                INSERT INTO practitioner_choice (
                    node_id, text, technique, next_node_id, feedback,
                    is_correct_technique, is_mistake, order_index
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                db.execute_insert(choice_query, (
                    node_id,
                    choice_data['text'],
                    choice_data['technique'],
                    choice_data['next_node_id'],
                    choice_data['feedback'],
                    choice_data['technique'].endswith('(complete)') or 
                    choice_data['technique'] == 'Simple reflection' or
                    'correct' in choice_data['technique'].lower(),
                    'mistake' in choice_data['technique'].lower() or
                    'non-MI' in choice_data['technique'],
                    j
                ))
                
                print(f"Created choice for node {node_data['id']}")
        
        print(f"Successfully imported Module {module_number}")
        return True
        
    except Exception as e:
        print(f"Error importing Module {module_number}: {e}")
        return False


def import_all_modules():
    """Import all MI modules from JSON files"""
    
    modules_dir = Path(__file__).parent / 'mi_modules'
    
    if not modules_dir.exists():
        print(f"Modules directory {modules_dir} not found")
        return False
    
    # Clear existing data
    print("Clearing existing data...")
    db.execute_query("DELETE FROM practitioner_choice", fetch='none')
    db.execute_query("DELETE FROM dialogue_node", fetch='none')
    db.execute_query("DELETE FROM dialogue_tree", fetch='none')
    db.execute_query("DELETE FROM mi_module", fetch='none')
    print("Existing data cleared")
    
    # Import modules 1-6
    success_count = 0
    for module_num in range(1, 7):
        json_file = modules_dir / f'module_{module_num}.json'
        
        if json_file.exists():
            if import_module_from_json(json_file, module_num):
                success_count += 1
        else:
            print(f"Module {module_num} JSON file not found: {json_file}")
    
    print(f"\nImport complete: {success_count}/6 modules imported successfully")
    return success_count == 6


if __name__ == '__main__':
    print("Starting MI Learning Platform data import...")
    
    # Test database connection
    try:
        test_query = "SELECT 1"
        result = db.execute_query(test_query)
        print("Database connection successful")
    except Exception as e:
        print(f"Database connection failed: {e}")
        sys.exit(1)
    
    # Import all modules
    if import_all_modules():
        print("All modules imported successfully!")
    else:
        print("Some modules failed to import")
        sys.exit(1)