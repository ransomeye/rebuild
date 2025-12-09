# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/storage/summary_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Persists final answers and SHAP explanations to database

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


class SummaryStore:
    """
    Stores final answers and SHAP explanations to PostgreSQL.
    """
    
    def __init__(self):
        """Initialize summary store with DB connection."""
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
        """Ensure summary table exists."""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ai_summaries (
                    summary_id SERIAL PRIMARY KEY,
                    conversation_id VARCHAR(255),
                    query TEXT,
                    answer TEXT,
                    shap_explanations JSONB,
                    verification JSONB,
                    model_version VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_summaries_conversation_id 
                ON ai_summaries(conversation_id)
            """)
            
            conn.commit()
            cur.close()
            logger.info("Summary table ensured")
        except Exception as e:
            logger.error(f"Error ensuring table: {e}")
    
    def save_summary(
        self,
        conversation_id: str,
        query: str,
        answer: str,
        shap_explanations: Optional[Dict[str, Any]] = None,
        verification: Optional[Dict[str, Any]] = None,
        model_version: Optional[str] = None
    ) -> Optional[int]:
        """
        Save summary to database.
        
        Args:
            conversation_id: Conversation ID
            query: User query
            answer: Final answer
            shap_explanations: SHAP explanations
            verification: Verification results
            model_version: Model version used
            
        Returns:
            Summary ID or None if failed
        """
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO ai_summaries (
                    conversation_id, query, answer,
                    shap_explanations, verification, model_version
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING summary_id
            """, (
                conversation_id,
                query,
                answer,
                json.dumps(shap_explanations) if shap_explanations else None,
                json.dumps(verification) if verification else None,
                model_version
            ))
            
            summary_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            logger.info(f"Saved summary {summary_id} for conversation {conversation_id}")
            return summary_id
            
        except Exception as e:
            logger.error(f"Error saving summary: {e}")
            return None
    
    def get_summary(self, summary_id: int) -> Optional[Dict[str, Any]]:
        """
        Get summary by ID.
        
        Args:
            summary_id: Summary ID
            
        Returns:
            Summary data or None
        """
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT * FROM ai_summaries
                WHERE summary_id = %s
            """, (summary_id,))
            
            row = cur.fetchone()
            cur.close()
            
            if not row:
                return None
            
            # Convert to dict
            columns = [desc[0] for desc in cur.description]
            result = dict(zip(columns, row))
            
            # Parse JSON fields
            for json_field in ['shap_explanations', 'verification']:
                if result.get(json_field):
                    result[json_field] = json.loads(result[json_field])
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting summary: {e}")
            return None
    
    def get_summaries_by_conversation(
        self,
        conversation_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all summaries for a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            List of summaries
        """
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT * FROM ai_summaries
                WHERE conversation_id = %s
                ORDER BY created_at DESC
            """, (conversation_id,))
            
            rows = cur.fetchall()
            cur.close()
            
            # Convert to dicts
            columns = [desc[0] for desc in cur.description]
            results = []
            for row in rows:
                result = dict(zip(columns, row))
                # Parse JSON fields
                for json_field in ['shap_explanations', 'verification']:
                    if result.get(json_field):
                        result[json_field] = json.loads(result[json_field])
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting summaries: {e}")
            return []

