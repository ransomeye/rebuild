# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/storage/ti_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: DB Interface for iocs and campaigns tables in PostgreSQL

import os
import json
import psycopg2
from typing import Dict, Any, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TIStore:
    """
    Database interface for IOCs and campaigns.
    """
    
    def __init__(self):
        """Initialize store with DB connection."""
        self.db_host = os.environ.get('DB_HOST', 'localhost')
        self.db_port = int(os.environ.get('DB_PORT', 5432))
        self.db_name = os.environ.get('DB_NAME', 'ransomeye')
        self.db_user = os.environ.get('DB_USER', 'gagan')
        self.db_pass = os.environ.get('DB_PASS', 'gagan')
        self.conn = None
        self._ensure_tables()
    
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
    
    def _ensure_tables(self):
        """Ensure tables exist."""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # IOCs table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS iocs (
                    id SERIAL PRIMARY KEY,
                    value TEXT NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    fingerprint VARCHAR(64) UNIQUE NOT NULL,
                    source VARCHAR(255),
                    source_id VARCHAR(255),
                    first_seen TIMESTAMP,
                    last_seen TIMESTAMP,
                    description TEXT,
                    tags JSONB,
                    confidence INTEGER,
                    trust_score FLOAT,
                    campaign_id INTEGER,
                    enrichment JSONB,
                    raw_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Campaigns table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS campaigns (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255),
                    description TEXT,
                    ioc_ids JSONB,
                    tags JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Indexes
            cur.execute("CREATE INDEX IF NOT EXISTS idx_iocs_fingerprint ON iocs(fingerprint)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_iocs_type ON iocs(type)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_iocs_campaign ON iocs(campaign_id)")
            
            conn.commit()
            cur.close()
            logger.info("TI tables ensured")
        except Exception as e:
            logger.error(f"Error ensuring tables: {e}")
    
    def save_ioc(self, ioc: Dict[str, Any], fingerprint: str) -> Optional[int]:
        """Save IOC to database."""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO iocs (
                    value, type, fingerprint, source, source_id,
                    first_seen, last_seen, description, tags, confidence,
                    trust_score, enrichment, raw_data
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fingerprint) DO UPDATE SET
                    last_seen = EXCLUDED.last_seen,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (
                ioc.get('value'),
                ioc.get('type'),
                fingerprint,
                ioc.get('source'),
                ioc.get('source_id'),
                ioc.get('first_seen'),
                ioc.get('last_seen'),
                ioc.get('description'),
                json.dumps(ioc.get('tags', [])),
                ioc.get('confidence'),
                ioc.get('trust_score'),
                json.dumps(ioc.get('enrichment', {})),
                json.dumps(ioc.get('raw', {}))
            ))
            
            ioc_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            return ioc_id
        except Exception as e:
            logger.error(f"Error saving IOC: {e}")
            return None
    
    def get_ioc_by_fingerprint(self, fingerprint: str) -> Optional[Dict[str, Any]]:
        """Get IOC by fingerprint."""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute("SELECT * FROM iocs WHERE fingerprint = %s", (fingerprint,))
            row = cur.fetchone()
            cur.close()
            
            if not row:
                return None
            
            columns = [desc[0] for desc in cur.description]
            result = dict(zip(columns, row))
            result['tags'] = json.loads(result['tags']) if result.get('tags') else []
            result['enrichment'] = json.loads(result['enrichment']) if result.get('enrichment') else {}
            result['raw_data'] = json.loads(result['raw_data']) if result.get('raw_data') else {}
            
            return result
        except Exception as e:
            logger.error(f"Error getting IOC: {e}")
            return None
    
    def get_similar_iocs(self, ioc_type: str, value: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get similar IOCs."""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT * FROM iocs
                WHERE type = %s AND value LIKE %s
                LIMIT %s
            """, (ioc_type, f'%{value[:20]}%', limit))
            
            rows = cur.fetchall()
            cur.close()
            
            columns = [desc[0] for desc in cur.description]
            results = []
            for row in rows:
                result = dict(zip(columns, row))
                result['tags'] = json.loads(result['tags']) if result.get('tags') else []
                results.append(result)
            
            return results
        except Exception as e:
            logger.error(f"Error getting similar IOCs: {e}")
            return []
    
    def save_campaign(self, campaign: Dict[str, Any]) -> Optional[int]:
        """Save campaign."""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO campaigns (name, description, ioc_ids, tags)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (
                campaign.get('name'),
                campaign.get('description'),
                json.dumps(campaign.get('ioc_ids', [])),
                json.dumps(campaign.get('tags', []))
            ))
            
            campaign_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            return campaign_id
        except Exception as e:
            logger.error(f"Error saving campaign: {e}")
            return None

