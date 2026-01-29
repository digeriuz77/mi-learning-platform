"""
Supabase Database Manager for MI Learning Platform
Replaces Django ORM with direct PostgreSQL access using psycopg2
"""
import os
import psycopg2
import psycopg2.extras
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import List, Dict, Optional, Any
import json


class SupabaseDB:
    """Database manager for Supabase PostgreSQL"""
    
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(
                host=os.environ.get('DB_HOST', 'localhost'),
                database=os.environ.get('DB_NAME', 'mi_learning'),
                user=os.environ.get('DB_USER', 'postgres'),
                password=os.environ.get('DB_PASSWORD', ''),
                port=os.environ.get('DB_PORT', '5432')
            )
            self.connection.autocommit = True
        except Exception as e:
            print(f"Database connection error: {e}")
            raise
    
    def execute_query(self, query: str, params: tuple = None, fetch: str = 'all') -> List[Dict]:
        """Execute a query and return results"""
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                if fetch == 'all':
                    return cursor.fetchall()
                elif fetch == 'one':
                    return cursor.fetchone()
                elif fetch == 'none':
                    return []
        except Exception as e:
            print(f"Query execution error: {e}")
            raise
    
    def execute_insert(self, query: str, params: tuple = None) -> int:
        """Execute insert query and return ID"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchone()[0] if cursor.description else None
        except Exception as e:
            print(f"Insert execution error: {e}")
            raise


class MIModuleManager:
    """Manager for MI learning modules"""
    
    def __init__(self, db: SupabaseDB):
        self.db = db
    
    def get_all_modules(self) -> List[Dict]:
        """Get all active MI modules"""
        query = """
        SELECT * FROM mi_module 
        WHERE is_active = TRUE 
        ORDER BY order_index, module_number
        """
        return self.db.execute_query(query)
    
    def get_module_by_id(self, module_id: int) -> Optional[Dict]:
        """Get specific module by ID"""
        query = "SELECT * FROM mi_module WHERE id = %s"
        return self.db.execute_query(query, (module_id,), fetch='one')
    
    def get_module_by_number(self, module_number: int) -> Optional[Dict]:
        """Get module by module number"""
        query = "SELECT * FROM mi_module WHERE module_number = %s AND is_active = TRUE"
        return self.db.execute_query(query, (module_number,), fetch='one')


class DialogueTreeManager:
    """Manager for dialogue trees and nodes"""
    
    def __init__(self, db: SupabaseDB):
        self.db = db
    
    def get_dialogue_tree(self, module_id: int) -> Optional[Dict]:
        """Get dialogue tree for a module"""
        query = "SELECT * FROM dialogue_tree WHERE module_id = %s"
        return self.db.execute_query(query, (module_id,), fetch='one')
    
    def get_node(self, node_id: str, tree_id: int) -> Optional[Dict]:
        """Get specific dialogue node"""
        query = """
        SELECT * FROM dialogue_node 
        WHERE node_id = %s AND tree_id = %s
        """
        return self.db.execute_query(query, (node_id, tree_id), fetch='one')
    
    def get_node_choices(self, node_id: int) -> List[Dict]:
        """Get practitioner choices for a node"""
        query = """
        SELECT * FROM practitioner_choice 
        WHERE node_id = %s 
        ORDER BY order_index, id
        """
        return self.db.execute_query(query, (node_id,))
    
    def get_start_node(self, module_id: int) -> Optional[Dict]:
        """Get starting node for a module"""
        query = """
        SELECT dn.* FROM dialogue_node dn
        JOIN dialogue_tree dt ON dn.tree_id = dt.id
        WHERE dt.module_id = %s AND dn.node_id = dt.start_node_id
        """
        return self.db.execute_query(query, (module_id,), fetch='one')


class UserProgressManager:
    """Manager for user progress tracking"""
    
    def __init__(self, db: SupabaseDB):
        self.db = db
    
    def get_or_create_progress(self, user_id: str, module_id: int) -> Dict:
        """Get or create user progress for a module"""
        # Try to get existing progress
        query = """
        SELECT * FROM user_module_progress 
        WHERE user_id = %s AND module_id = %s
        """
        existing = self.db.execute_query(query, (user_id, module_id), fetch='one')
        
        if existing:
            return existing
        
        # Create new progress record
        insert_query = """
        INSERT INTO user_module_progress (user_id, module_id, completion_status)
        VALUES (%s, %s, 'not_started')
        RETURNING *
        """
        return self.db.execute_query(insert_query, (user_id, module_id), fetch='one')
    
    def update_progress(self, user_id: str, module_id: int, node_id: str, 
                       choice_id: int, is_correct: bool, points: int) -> Dict:
        """Update user progress after making a choice"""
        # Record the attempt
        attempt_query = """
        INSERT INTO user_attempt (user_id, node_id, choice_id, is_correct, points_earned)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """
        self.db.execute_insert(attempt_query, (user_id, choice_id, is_correct, points))
        
        # Update progress
        progress_query = """
        UPDATE user_module_progress 
        SET current_node_id = %s,
            nodes_completed = array_append(nodes_completed, %s),
            completion_status = 'in_progress'
        WHERE user_id = %s AND module_id = %s
        RETURNING *
        """
        return self.db.execute_query(progress_query, (node_id, node_id, user_id, module_id), fetch='one')
    
    def complete_module(self, user_id: str, module_id: int, score: int, status: str) -> Dict:
        """Mark module as completed"""
        query = """
        UPDATE user_module_progress 
        SET completion_status = %s, completion_score = %s, completed_at = NOW()
        WHERE user_id = %s AND module_id = %s
        RETURNING *
        """
        return self.db.execute_query(query, (status, score, user_id, module_id), fetch='one')
    
    def get_user_progress(self, user_id: str) -> List[Dict]:
        """Get all progress for a user"""
        query = """
        SELECT ump.*, mi.title as module_title, mi.module_number
        FROM user_module_progress ump
        JOIN mi_module mi ON ump.module_id = mi.id
        WHERE ump.user_id = %s
        ORDER BY mi.module_number
        """
        return self.db.execute_query(query, (user_id,))


class UserScoreManager:
    """Manager for user scores and statistics"""
    
    def __init__(self, db: SupabaseDB):
        self.db = db
    
    def get_user_score(self, user_id: str) -> Optional[Dict]:
        """Get user's overall score"""
        query = "SELECT * FROM user_score WHERE user_id = %s"
        return self.db.execute_query(query, (user_id,), fetch='one')
    
    def get_leaderboard(self, limit: int = 50) -> List[Dict]:
        """Get leaderboard data"""
        query = """
        SELECT us.*, au.username, au.first_name
        FROM user_score us
        JOIN app_user au ON us.user_id = au.id
        ORDER BY us.total_points DESC, us.modules_completed DESC
        LIMIT %s
        """
        return self.db.execute_query(query, (limit,))
    
    def update_user_score(self, user_id: str) -> Dict:
        """Trigger user score recalculation"""
        query = "SELECT update_user_score(%s)"
        self.db.execute_query(query, (user_id,), fetch='none')
        return self.get_user_score(user_id)


# Database instance and managers (lazy initialization)
db = None
module_manager = None
dialogue_manager = None
progress_manager = None
score_manager = None

def initialize_managers():
    """Initialize database connection and managers"""
    global db, module_manager, dialogue_manager, progress_manager, score_manager
    
    if db is None:
        db = SupabaseDB()
        module_manager = MIModuleManager(db)
        dialogue_manager = DialogueTreeManager(db)
        progress_manager = UserProgressManager(db)
        score_manager = UserScoreManager(db)
    
    return db, module_manager, dialogue_manager, progress_manager, score_manager