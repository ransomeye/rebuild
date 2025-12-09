# Path and File Name : /home/ransomeye/rebuild/ransomeye_orchestrator/rehydrate/state_reconciler.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Merges imported data with existing DB using idempotency

import os
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class StateReconciler:
    """Merges imported data with existing DB using idempotency."""
    
    def __init__(self):
        """Initialize state reconciler."""
        self.db_host = os.environ.get('DB_HOST', 'localhost')
        self.db_port = int(os.environ.get('DB_PORT', '5432'))
        self.db_name = os.environ.get('DB_NAME', 'ransomeye')
        self.db_user = os.environ.get('DB_USER', 'gagan')
        self.db_pass = os.environ.get('DB_PASS', 'gagan')
        self._ensure_idempotency_table()
    
    def _get_connection(self):
        """Get database connection."""
        return psycopg2.connect(
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            user=self.db_user,
            password=self.db_pass
        )
    
    def _ensure_idempotency_table(self):
        """Ensure idempotency tracking table exists."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orchestrator_idempotency (
                    idempotency_key VARCHAR(255) PRIMARY KEY,
                    incident_id VARCHAR(255) NOT NULL,
                    processed_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    status VARCHAR(50) NOT NULL
                )
            """)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to ensure idempotency table: {e}")
        finally:
            conn.close()
    
    def check_idempotency(self, idempotency_key: str) -> bool:
        """
        Check if idempotency key has been processed.
        
        Args:
            idempotency_key: Idempotency key
        
        Returns:
            True if already processed
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM orchestrator_idempotency
                WHERE idempotency_key = %s
            """, (idempotency_key,))
            return cursor.fetchone() is not None
        finally:
            conn.close()
    
    def record_idempotency(self, idempotency_key: str, incident_id: str):
        """
        Record idempotency key processing.
        
        Args:
            idempotency_key: Idempotency key
            incident_id: Incident identifier
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO orchestrator_idempotency (
                    idempotency_key, incident_id, status
                ) VALUES (%s, %s, 'completed')
                ON CONFLICT (idempotency_key) DO NOTHING
            """, (idempotency_key, incident_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to record idempotency: {e}")
        finally:
            conn.close()
    
    def restore_timeline(self, timeline_path: Path, incident_id: str, idempotency_key: Optional[str] = None):
        """
        Restore timeline data.
        
        Args:
            timeline_path: Path to timeline JSON file
            incident_id: Incident identifier
            idempotency_key: Optional idempotency key
        """
        with open(timeline_path, 'r') as f:
            timeline_data = json.load(f)
        
        # Use KillChain API to restore timeline
        # For now, log the restoration
        logger.info(f"Restoring timeline for incident {incident_id}: {len(timeline_data)} entries")
        
        # TODO: Implement actual timeline restoration via API
        # This would call the KillChain API to insert timeline entries
    
    def restore_alerts(self, alerts_path: Path, incident_id: str, idempotency_key: Optional[str] = None):
        """
        Restore alerts using ON CONFLICT logic.
        
        Args:
            alerts_path: Path to alerts JSON file
            incident_id: Incident identifier
            idempotency_key: Optional idempotency key
        """
        with open(alerts_path, 'r') as f:
            alerts = json.load(f)
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            for alert in alerts:
                # Use ON CONFLICT DO NOTHING to handle duplicates
                # Assuming alerts table has unique constraint on (id, timestamp)
                cursor.execute("""
                    INSERT INTO alerts (
                        id, timestamp, alert_type, severity, source, title,
                        description, raw_data, status, created_at, updated_at,
                        correlation_id
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (id, timestamp) DO NOTHING
                """, (
                    alert.get('id'),
                    alert.get('timestamp'),
                    alert.get('alert_type'),
                    alert.get('severity'),
                    alert.get('source'),
                    alert.get('title'),
                    alert.get('description'),
                    json.dumps(alert.get('raw_data')) if alert.get('raw_data') else None,
                    alert.get('status', 'open'),
                    alert.get('created_at'),
                    alert.get('updated_at'),
                    alert.get('correlation_id')
                ))
            
            conn.commit()
            logger.info(f"Restored {len(alerts)} alerts for incident {incident_id}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to restore alerts: {e}")
            raise
        finally:
            conn.close()

