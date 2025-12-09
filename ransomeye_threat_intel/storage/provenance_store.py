# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/storage/provenance_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Tracks source history (Table: ioc_provenance) for every normalized IOC

import os
import json
import psycopg2
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProvenanceStore:
    """
    Tracks provenance (source history) for IOCs.
    Stores source ID, timestamp, and origin information.
    """
    
    def __init__(self):
        """Initialize provenance store."""
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
        """Ensure provenance table exists."""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ioc_provenance (
                    id SERIAL PRIMARY KEY,
                    ioc_id INTEGER REFERENCES iocs(id),
                    fingerprint VARCHAR(64),
                    source VARCHAR(255) NOT NULL,
                    source_id VARCHAR(255),
                    source_url TEXT,
                    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB
                )
            """)
            
            cur.execute("CREATE INDEX IF NOT EXISTS idx_provenance_fingerprint ON ioc_provenance(fingerprint)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_provenance_ioc_id ON ioc_provenance(ioc_id)")
            
            conn.commit()
            cur.close()
            logger.info("Provenance table ensured")
        except Exception as e:
            logger.error(f"Error ensuring provenance table: {e}")
    
    def record_provenance(
        self,
        ioc_id: Optional[int],
        fingerprint: str,
        source: str,
        source_id: Optional[str] = None,
        source_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Record provenance for an IOC.
        
        Args:
            ioc_id: IOC database ID
            fingerprint: IOC fingerprint
            source: Source identifier
            source_id: Source-specific ID
            source_url: Source URL
            metadata: Additional metadata
            
        Returns:
            Provenance record ID
        """
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO ioc_provenance (
                    ioc_id, fingerprint, source, source_id, source_url, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                ioc_id,
                fingerprint,
                source,
                source_id,
                source_url,
                json.dumps(metadata) if metadata else None
            ))
            
            prov_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            return prov_id
        except Exception as e:
            logger.error(f"Error recording provenance: {e}")
            return None
    
    def get_provenance(self, fingerprint: str) -> List[Dict[str, Any]]:
        """Get all provenance records for an IOC."""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT * FROM ioc_provenance
                WHERE fingerprint = %s
                ORDER BY ingested_at DESC
            """, (fingerprint,))
            
            rows = cur.fetchall()
            cur.close()
            
            columns = [desc[0] for desc in cur.description]
            results = []
            for row in rows:
                result = dict(zip(columns, row))
                result['metadata'] = json.loads(result['metadata']) if result.get('metadata') else {}
                results.append(result)
            
            return results
        except Exception as e:
            logger.error(f"Error getting provenance: {e}")
            return []

