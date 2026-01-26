#!/usr/bin/env python3
"""
Import MI Dialogue Modules into Supabase PostgreSQL
Direct database approach - no Django migrations needed!
"""

import psycopg2
import json
import os
from dotenv import load_dotenv

load_dotenv()

def import_mi_module(module_number, json_file_path):
    """Import a single MI dialogue module into database"""
    
    conn = psycopg2.connect(
        dbname=os.environ.get('DB_NAME', 'mi_learning'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', ''),
        host=os.environ.get('DB_HOST', 'localhost'),
        port=os.environ.get('DB_PORT', '5432')
    )
    
    cur = conn.cursor()
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            module_data = json.load(f)
        
        dialogue_tree_data = module_data['dialogue_tree']
        
        print(f"Importing Module {module_number}: {dialogue_tree_data['title']}")
        
        # Create Scenario record
        cur.execute("""
            INSERT INTO game_scenario (title, description, scenario_type, module_number, difficulty, points)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            dialogue_tree_data['title'],
            dialogue_tree_data['description'],
            'scenario',
            module_number,
            'beginner' if module_number <= 2 else 'intermediate',
            500
        ))
        
        scenario_id = cur.fetchone()[0]
        
        # Create DialogueTree record
        cur.execute("""
            INSERT INTO game_dialoguetree (title, learning_objective, technique_focus, stage_of_change, mi_process, description, start_node, module_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            dialogue_tree_data['title'],
            dialogue_tree_data['learning_objective'],
            dialogue_tree_data['technique_focus'],
            dialogue_tree_data['stage_of_change'],
            dialogue_tree_data['mi_process'],
            dialogue_tree_data['description'],
            dialogue_tree_data['start_node'],
            module_number
        ))
        
        tree_id = cur.fetchone()[0]
        
        # Import Dialogue Nodes
        node_mapping = {}
        for node_data in dialogue_tree_data['nodes']:
            cur.execute("""
                INSERT INTO game_dialoguenode (tree_id, node_id, patient_statement, patient_context, change_talk_present, change_talk_type, is_ending, outcome, learning_summary, order_num)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                tree_id,
                node_data['id'],
                node_data.get('patient_statement', ''),
                node_data.get('patient_context', ''),
                node_data.get('change_talk_present', False),
                node_data.get('change_talk_type', ''),
                node_data.get('is_ending', False),
                node_data.get('outcome', ''),
                node_data.get('learning_summary', ''),
                int(node_data['id'].split('_')[-1]) if '_' in node_data['id'] else 0
            ))
            
            node_db_id = cur.fetchone()[0]
            node_mapping[node_data['id']] = node_db_id
            
            # Import Practitioner Choices
            if 'practitioner_choices' in node_data:
                for choice_data in node_data['practitioner_choices']:
                    cur.execute("""
                        INSERT INTO game_practitionerchoice (node_id, text, technique, next_node_id, feedback, is_correct_technique, is_mistake)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        node_db_id,
                        choice_data['text'],
                        choice_data['technique'],
                        choice_data['next_node_id'],
                        choice_data['feedback'],
                        'effective' in choice_data.get('technique', '').lower(),
                        'ineffective' in choice_data.get('technique', '').lower() or 'non-MI' in choice_data.get('technique', '').lower()
                    ))
        
        conn.commit()
        print(f"✅ Module {module_number} imported successfully!")
        print(f"   - {len(dialogue_tree_data['nodes'])} dialogue nodes")
        print(f"   - Scenario ID: {scenario_id}")
        print(f"   - Tree ID: {tree_id}")
        
        return scenario_id
        
    except Exception as e:
        print(f"❌ Error importing module {module_number}: {e}")
        conn.rollback()
        return None
        
    finally:
        cur.close()
        conn.close()

def import_all_modules():
    """Import all 6 MI dialogue modules"""
    
    modules_imported = 0
    
    for module_num in range(1, 7):
        json_file = f"mi_modules/module_{module_num}.json"
        
        if os.path.exists(json_file):
            scenario_id = import_mi_module(module_num, json_file)
            if scenario_id:
                modules_imported += 1
        else:
            print(f"⚠️ Could not find {json_file}")
    
    print(f"\n🎯 Import Summary:")
    print(f"   Modules imported: {modules_imported}/6")
    print(f"   Ready for MI Learning Platform!")
    
    if modules_imported == 6:
        print("🎉 All MI dialogue modules imported successfully!")
        print("📚 Available modules:")
        print("   1. Simple Reflections - Building Engagement")
        print("   2. Open-Ended Questions - Inviting Exploration") 
        print("   3. Complex & Double-Sided Reflections - Exploring Ambivalence")
        print("   4. Affirmations - Recognizing Strengths")
        print("   5. Summarizing - Linking and Transitioning")
        print("   6. Change Talk Recognition & Evocation (DARN-CAT)")

if __name__ == "__main__":
    print("Importing MI Dialogue Modules...")
    import_all_modules()
    print("Ready to start MI Learning Platform!")