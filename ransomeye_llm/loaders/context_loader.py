# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm/loaders/context_loader.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Fetches data from Alert Engine, KillChain, and Forensics

import os
import sys
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContextLoader:
    """
    Loads context data from Alert Engine, KillChain, and Forensics.
    """
    
    def __init__(self):
        """Initialize context loader."""
        self.db_engine = None
        self.SessionLocal = None
        self._initialize_db()
        
        # API endpoints
        self.killchain_url = os.environ.get('KILLCHAIN_API_URL', 'http://localhost:8005')
        self.forensic_url = os.environ.get('FORENSIC_API_URL', 'http://localhost:8006')
    
    def _initialize_db(self):
        """Initialize database connection."""
        db_host = os.environ.get('DB_HOST', 'localhost')
        db_port = os.environ.get('DB_PORT', '5432')
        db_name = os.environ.get('DB_NAME', 'ransomeye')
        db_user = os.environ.get('DB_USER', 'gagan')
        db_pass = os.environ.get('DB_PASS', 'gagan')
        
        connection_string = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        
        try:
            self.db_engine = create_engine(connection_string, pool_pre_ping=True, echo=False)
            self.SessionLocal = sessionmaker(bind=self.db_engine, autocommit=False, autoflush=False)
            logger.info("Context loader database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    @contextmanager
    def get_session(self):
        """Context manager for database sessions."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    async def load_context(self, incident_id: str) -> Dict[str, Any]:
        """
        Load complete context for an incident.
        
        Args:
            incident_id: Incident identifier
            
        Returns:
            Context dictionary with all data
        """
        context = {
            'incident_id': incident_id,
            'alerts': [],
            'timeline': None,
            'forensic_artifacts': [],
            'iocs': {},
            'shap_values': {}
        }
        
        # Load alerts from database
        context['alerts'] = await self._load_alerts(incident_id)
        
        # Load timeline from KillChain API
        context['timeline'] = await self._load_timeline(incident_id)
        
        # Load forensic artifacts
        context['forensic_artifacts'] = await self._load_forensic_artifacts(incident_id)
        
        # Extract IOCs
        context['iocs'] = self._extract_iocs(context)
        
        # Load SHAP values (from alerts or AI Core)
        context['shap_values'] = await self._load_shap_values(incident_id)
        
        return context
    
    async def _load_alerts(self, incident_id: str) -> List[Dict[str, Any]]:
        """
        Load alerts from database.
        
        Args:
            incident_id: Incident identifier
            
        Returns:
            List of alert dictionaries
        """
        try:
            with self.get_session() as session:
                # Query alerts table (assuming it exists from Alert Engine)
                query = text("""
                    SELECT alert_id, alert_type, source, target, severity, 
                           timestamp, metadata, matches
                    FROM alerts
                    WHERE incident_id = :incident_id
                    ORDER BY timestamp DESC
                    LIMIT 100
                """)
                
                result = session.execute(query, {'incident_id': incident_id})
                alerts = []
                
                for row in result:
                    alerts.append({
                        'alert_id': row[0],
                        'alert_type': row[1],
                        'source': row[2],
                        'target': row[3],
                        'severity': row[4],
                        'timestamp': str(row[5]) if row[5] else None,
                        'metadata': row[6] if row[6] else {},
                        'matches': row[7] if row[7] else []
                    })
                
                logger.info(f"Loaded {len(alerts)} alerts for incident {incident_id}")
                return alerts
                
        except Exception as e:
            logger.warning(f"Failed to load alerts: {e}")
            return []
    
    async def _load_timeline(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """
        Load timeline from KillChain API.
        
        Args:
            incident_id: Incident identifier
            
        Returns:
            Timeline dictionary or None
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.killchain_url}/timeline/{incident_id}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('timeline')
                    else:
                        logger.warning(f"Failed to load timeline: {response.status}")
                        return None
        except Exception as e:
            logger.warning(f"Failed to load timeline from API: {e}")
            return None
    
    async def _load_forensic_artifacts(self, incident_id: str) -> List[Dict[str, Any]]:
        """
        Load forensic artifacts.
        
        Args:
            incident_id: Incident identifier
            
        Returns:
            List of forensic artifact dictionaries
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.forensic_url}/ledger/entries"
                async with session.get(url, params={'limit': 50}) as response:
                    if response.status == 200:
                        data = await response.json()
                        entries = data.get('entries', [])
                        # Filter by incident_id if available in metadata
                        filtered = [
                            e for e in entries
                            if e.get('metadata', {}).get('incident_id') == incident_id
                        ]
                        return filtered
                    else:
                        return []
        except Exception as e:
            logger.warning(f"Failed to load forensic artifacts: {e}")
            return []
    
    def _extract_iocs(self, context: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Extract IOCs from context.
        
        Args:
            context: Context dictionary
            
        Returns:
            Dictionary of IOC types to values
        """
        iocs = {
            'ips': [],
            'domains': [],
            'hashes': [],
            'files': []
        }
        
        # Extract from alerts
        for alert in context.get('alerts', []):
            source = alert.get('source', '')
            target = alert.get('target', '')
            
            # Check if source/target are IPs
            if self._is_ip(source):
                if source not in iocs['ips']:
                    iocs['ips'].append(source)
            if self._is_ip(target):
                if target not in iocs['ips']:
                    iocs['ips'].append(target)
            
            # Extract from metadata
            metadata = alert.get('metadata', {})
            if 'ip' in metadata:
                ip_val = metadata['ip']
                if ip_val not in iocs['ips']:
                    iocs['ips'].append(ip_val)
            if 'domain' in metadata:
                domain = metadata['domain']
                if domain not in iocs['domains']:
                    iocs['domains'].append(domain)
            if 'hash' in metadata:
                hash_val = metadata['hash']
                if hash_val not in iocs['hashes']:
                    iocs['hashes'].append(hash_val)
        
        return iocs
    
    def _is_ip(self, value: str) -> bool:
        """Check if value is an IP address."""
        import re
        ip_pattern = re.compile(
            r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        )
        return bool(ip_pattern.match(value))
    
    async def _load_shap_values(self, incident_id: str) -> Dict[str, float]:
        """
        Load SHAP values for incident.
        
        Args:
            incident_id: Incident identifier
            
        Returns:
            Dictionary of feature names to SHAP values
        """
        try:
            with self.get_session() as session:
                # Query for SHAP values (assuming they're stored in alerts or separate table)
                query = text("""
                    SELECT shap_values
                    FROM alerts
                    WHERE incident_id = :incident_id
                    AND shap_values IS NOT NULL
                    LIMIT 1
                """)
                
                result = session.execute(query, {'incident_id': incident_id})
                row = result.fetchone()
                
                if row and row[0]:
                    import json
                    return json.loads(row[0]) if isinstance(row[0], str) else row[0]
                
                return {}
        except Exception as e:
            logger.warning(f"Failed to load SHAP values: {e}")
            return {}

