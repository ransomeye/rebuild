# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/storage/conversation_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Persists full agent traces to PostgreSQL database

import os
import sys
import json
import psycopg2
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConversationStore:
    """
    Stores full agent traces and conversations to PostgreSQL.
    """
    
    def __init__(self):
        """Initialize conversation store with DB connection."""
        self.db_host = os.environ.get('DB_HOST', 'localhost')
        self.db_port = int(os.environ.get('DB_PORT', 5432))
        self.db_name = os.environ.get('DB_NAME', 'ransomeye')
        self.db_user = os.environ.get('DB_USER', 'gagan')
        self.db_pass = os.environ.get('DB_PASS', 'gagan')
        
        self.conn = None
        self._ensure_table()
    
    def _get_connection(self):
        """Get database connection."""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_pass
            )
        return self.conn
    
    def _ensure_table(self):
        """Ensure conversation table exists."""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ai_conversations (
                    conversation_id VARCHAR(255) PRIMARY KEY,
                    user_id VARCHAR(255),
                    query TEXT,
                    answer TEXT,
                    agent_trace JSONB,
                    intermediate_results JSONB,
                    verification JSONB,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_conversations_user_id 
                ON ai_conversations(user_id)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_conversations_created_at 
                ON ai_conversations(created_at)
            """)
            
            conn.commit()
            cur.close()
            logger.info("Conversation table ensured")
        except Exception as e:
            logger.error(f"Error ensuring table: {e}")
    
    def save_conversation(
        self,
        conversation_id: str,
        user_id: Optional[str],
        query: str,
        answer: str,
        agent_trace: Dict[str, Any],
        intermediate_results: Dict[str, Any],
        verification: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save conversation to database.
        
        Args:
            conversation_id: Unique conversation ID
            user_id: Optional user ID
            query: User query
            answer: Final answer
            agent_trace: Full agent execution trace
            intermediate_results: Intermediate results from agents
            verification: Verification results
            metadata: Additional metadata
            
        Returns:
            True if saved successfully
        """
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO ai_conversations (
                    conversation_id, user_id, query, answer,
                    agent_trace, intermediate_results, verification, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (conversation_id) DO UPDATE SET
                    answer = EXCLUDED.answer,
                    agent_trace = EXCLUDED.agent_trace,
                    intermediate_results = EXCLUDED.intermediate_results,
                    verification = EXCLUDED.verification,
                    metadata = EXCLUDED.metadata,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                conversation_id,
                user_id,
                query,
                answer,
                json.dumps(agent_trace),
                json.dumps(intermediate_results),
                json.dumps(verification) if verification else None,
                json.dumps(metadata) if metadata else None
            ))
            
            conn.commit()
            cur.close()
            logger.info(f"Saved conversation {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            return False
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get conversation by ID.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Conversation data or None
        """
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT * FROM ai_conversations
                WHERE conversation_id = %s
            """, (conversation_id,))
            
            row = cur.fetchone()
            cur.close()
            
            if not row:
                return None
            
            # Convert to dict
            columns = [desc[0] for desc in cur.description]
            result = dict(zip(columns, row))
            
            # Parse JSON fields
            for json_field in ['agent_trace', 'intermediate_results', 'verification', 'metadata']:
                if result.get(json_field):
                    result[json_field] = json.loads(result[json_field])
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting conversation: {e}")
            return None
    
    def list_conversations(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List conversations.
        
        Args:
            user_id: Optional user ID filter
            limit: Maximum results
            offset: Offset for pagination
            
        Returns:
            List of conversations
        """
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            if user_id:
                cur.execute("""
                    SELECT * FROM ai_conversations
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, (user_id, limit, offset))
            else:
                cur.execute("""
                    SELECT * FROM ai_conversations
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, (limit, offset))
            
            rows = cur.fetchall()
            cur.close()
            
            # Convert to dicts
            columns = [desc[0] for desc in cur.description]
            results = []
            for row in rows:
                result = dict(zip(columns, row))
                # Parse JSON fields
                for json_field in ['agent_trace', 'intermediate_results', 'verification', 'metadata']:
                    if result.get(json_field):
                        result[json_field] = json.loads(result[json_field])
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error listing conversations: {e}")
            return []

