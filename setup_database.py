#!/usr/bin/env python3
"""
Direct Database Setup for MI Learning Platform
Using Supabase PostgreSQL - no Django migrations needed!
"""

import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_mi_database():
    """Set up MI Learning Platform database tables directly"""
    
    # Database connection
    conn = psycopg2.connect(
        dbname=os.environ.get('DB_NAME', 'mi_learning'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', ''),
        host=os.environ.get('DB_HOST', 'localhost'),
        port=os.environ.get('DB_PORT', '5432')
    )
    
    cur = conn.cursor()
    
    try:
        # Create tables for MI Learning Platform
        
        # Scenarios table (replaces challenges)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS game_scenario (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                scenario_type VARCHAR(10) DEFAULT 'scenario',
                module_number INTEGER NOT NULL,
                difficulty VARCHAR(15) DEFAULT 'beginner',
                order_num INTEGER DEFAULT 0,
                points INTEGER DEFAULT 100,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Dialogue Trees table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS game_dialoguetree (
                id SERIAL PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                learning_objective TEXT,
                technique_focus VARCHAR(100),
                stage_of_change VARCHAR(50),
                mi_process VARCHAR(50),
                description TEXT,
                start_node VARCHAR(20),
                module_number INTEGER NOT NULL
            );
        """)
        
        # Dialogue Nodes table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS game_dialoguenode (
                id SERIAL PRIMARY KEY,
                tree_id INTEGER REFERENCES game_dialoguetree(id),
                node_id VARCHAR(20) NOT NULL,
                patient_statement TEXT,
                patient_context TEXT,
                change_talk_present BOOLEAN DEFAULT FALSE,
                change_talk_type VARCHAR(10),
                is_ending BOOLEAN DEFAULT FALSE,
                outcome TEXT,
                learning_summary TEXT,
                order_num INTEGER DEFAULT 0
            );
        """)
        
        # Practitioner Choices table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS game_practitionerchoice (
                id SERIAL PRIMARY KEY,
                node_id INTEGER REFERENCES game_dialoguenode(id),
                text VARCHAR(500),
                technique VARCHAR(100),
                next_node_id VARCHAR(20),
                feedback TEXT,
                is_correct_technique BOOLEAN DEFAULT FALSE,
                is_mistake BOOLEAN DEFAULT FALSE
            );
        """)
        
        # Module Progress table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS game_moduleprogress (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES auth_user(id),
                scenario_id INTEGER REFERENCES game_scenario(id),
                nodes_completed JSONB DEFAULT '[]',
                current_node VARCHAR(20) DEFAULT 'start',
                techniques_demonstrated JSONB DEFAULT '[]',
                completion_status VARCHAR(20) DEFAULT 'not_started',
                completion_score INTEGER DEFAULT 0,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            );
        """)
        
        # User Score table  
        cur.execute("""
            CREATE TABLE IF NOT EXISTS game_userscore (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES auth_user(id) UNIQUE,
                total_points INTEGER DEFAULT 0,
                scenarios_completed INTEGER DEFAULT 0,
                modules_completed INTEGER DEFAULT 0,
                technique_mastery JSONB DEFAULT '{}',
                change_talk_evoked INTEGER DEFAULT 0,
                reflections_offered INTEGER DEFAULT 0,
                summaries_created INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # MI Questions table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS game_miquestion (
                id SERIAL PRIMARY KEY,
                scenario_id INTEGER REFERENCES game_scenario(id),
                patient_statement TEXT,
                client_context TEXT,
                dialogue_prompt TEXT,
                technique_focus VARCHAR(50),
                hint TEXT,
                points INTEGER DEFAULT 100,
                change_talk_present BOOLEAN DEFAULT FALSE,
                change_talk_type VARCHAR(10)
            );
        """)
        
        conn.commit()
        print("✅ MI Learning Platform database created successfully!")
        
        # Create indexes for performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_scenario_module ON game_scenario(module_number);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_dialogue_tree_module ON game_dialoguetree(module_number);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_progress_user ON game_moduleprogress(user_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_node_tree ON game_dialoguenode(tree_id);")
        
        conn.commit()
        print("✅ Database indexes created!")
        
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        conn.rollback()
        
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    print("Setting up MI Learning Platform Database...")
    setup_mi_database()
    print("Database setup complete! Ready to import MI dialogue modules.")