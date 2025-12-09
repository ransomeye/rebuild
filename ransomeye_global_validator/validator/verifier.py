# Path and File Name : /home/ransomeye/rebuild/ransomeye_global_validator/validator/verifier.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Verifies validation results by checking DB/API for expected artifacts with exponential backoff

import os
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Verifier:
    """Verifies validation results by checking database and APIs."""
    
    def __init__(self):
        """Initialize verifier with database connection."""
        self.engine = None
        self.SessionLocal = None
        self._initialize_db()
        logger.info("Verifier initialized")
    
    def _initialize_db(self):
        """Initialize database connection."""
        db_host = os.environ.get('DB_HOST', 'localhost')
        db_port = os.environ.get('DB_PORT', '5432')
        db_name = os.environ.get('DB_NAME', 'ransomeye')
        db_user = os.environ.get('DB_USER', 'gagan')
        db_pass = os.environ.get('DB_PASS', 'gagan')
        
        connection_string = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        
        try:
            self.engine = create_engine(connection_string, pool_pre_ping=True, echo=False)
            self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
            logger.info("Verifier database connection initialized")
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
    
    async def verify_alert_in_db(self, alert_id: str, max_wait_seconds: int = 60) -> Dict[str, Any]:
        """
        Verify alert exists in database with exponential backoff.
        
        Args:
            alert_id: Alert identifier
            max_wait_seconds: Maximum time to wait
            
        Returns:
            Verification result
        """
        start_time = datetime.utcnow()
        wait_interval = 1  # Start with 1 second
        max_interval = 10  # Max 10 seconds between checks
        
        while (datetime.utcnow() - start_time).total_seconds() < max_wait_seconds:
            try:
                with self.get_session() as session:
                    result = session.execute(
                        text("SELECT alert_id, source, alert_type, target, severity, created_at FROM alerts WHERE alert_id = :alert_id"),
                        {"alert_id": alert_id}
                    ).fetchone()
                    
                    if result:
                        logger.info(f"Alert {alert_id} found in database")
                        return {
                            "success": True,
                            "alert_id": result[0],
                            "source": result[1],
                            "alert_type": result[2],
                            "target": result[3],
                            "severity": result[4],
                            "created_at": result[5].isoformat() if result[5] else None,
                            "wait_time_seconds": (datetime.utcnow() - start_time).total_seconds()
                        }
            
            except Exception as e:
                logger.warning(f"Error checking alert in DB: {e}")
            
            # Exponential backoff
            await asyncio.sleep(wait_interval)
            wait_interval = min(wait_interval * 2, max_interval)
        
        logger.error(f"Alert {alert_id} not found in database after {max_wait_seconds} seconds")
        return {
            "success": False,
            "error": f"Alert not found after {max_wait_seconds} seconds",
            "wait_time_seconds": max_wait_seconds
        }
    
    async def verify_incident_created(self, incident_id: str, max_wait_seconds: int = 60) -> Dict[str, Any]:
        """
        Verify incident was created in KillChain timeline store.
        
        Args:
            incident_id: Incident identifier
            max_wait_seconds: Maximum time to wait
            
        Returns:
            Verification result
        """
        start_time = datetime.utcnow()
        wait_interval = 1
        max_interval = 10
        
        while (datetime.utcnow() - start_time).total_seconds() < max_wait_seconds:
            try:
                with self.get_session() as session:
                    # Check timeline_store table
                    result = session.execute(
                        text("SELECT timeline_id, incident_id, created_at FROM timeline_records WHERE incident_id = :incident_id"),
                        {"incident_id": incident_id}
                    ).fetchone()
                    
                    if result:
                        logger.info(f"Incident {incident_id} found in timeline store")
                        return {
                            "success": True,
                            "timeline_id": str(result[0]),
                            "incident_id": str(result[1]),
                            "created_at": result[2].isoformat() if result[2] else None,
                            "wait_time_seconds": (datetime.utcnow() - start_time).total_seconds()
                        }
            
            except Exception as e:
                logger.warning(f"Error checking incident in DB: {e}")
            
            await asyncio.sleep(wait_interval)
            wait_interval = min(wait_interval * 2, max_interval)
        
        logger.error(f"Incident {incident_id} not found after {max_wait_seconds} seconds")
        return {
            "success": False,
            "error": f"Incident not found after {max_wait_seconds} seconds",
            "wait_time_seconds": max_wait_seconds
        }
    
    async def verify_evidence_logged(self, file_hash_sha256: str, incident_id: Optional[str] = None, 
                                     max_wait_seconds: int = 90) -> Dict[str, Any]:
        """
        Verify evidence was logged in forensic database.
        
        Args:
            file_hash_sha256: SHA256 hash of the file
            incident_id: Optional incident ID to filter by
            max_wait_seconds: Maximum time to wait
            
        Returns:
            Verification result
        """
        start_time = datetime.utcnow()
        wait_interval = 2
        max_interval = 15
        
        while (datetime.utcnow() - start_time).total_seconds() < max_wait_seconds:
            try:
                with self.get_session() as session:
                    if incident_id:
                        result = session.execute(
                            text("""
                                SELECT evidence_id, incident_id, evidence_type, file_hash_sha256, 
                                       collected_at, source_host
                                FROM evidence_ledger 
                                WHERE file_hash_sha256 = :hash AND incident_id = :incident_id
                            """),
                            {"hash": file_hash_sha256, "incident_id": incident_id}
                        ).fetchone()
                    else:
                        result = session.execute(
                            text("""
                                SELECT evidence_id, incident_id, evidence_type, file_hash_sha256, 
                                       collected_at, source_host
                                FROM evidence_ledger 
                                WHERE file_hash_sha256 = :hash
                            """),
                            {"hash": file_hash_sha256}
                        ).fetchone()
                    
                    if result:
                        logger.info(f"Evidence with hash {file_hash_sha256[:16]}... found in database")
                        return {
                            "success": True,
                            "evidence_id": str(result[0]),
                            "incident_id": str(result[1]),
                            "evidence_type": result[2],
                            "file_hash_sha256": result[3],
                            "collected_at": result[4].isoformat() if result[4] else None,
                            "source_host": result[5],
                            "wait_time_seconds": (datetime.utcnow() - start_time).total_seconds()
                        }
            
            except Exception as e:
                logger.warning(f"Error checking evidence in DB: {e}")
            
            await asyncio.sleep(wait_interval)
            wait_interval = min(wait_interval * 2, max_interval)
        
        logger.error(f"Evidence with hash {file_hash_sha256[:16]}... not found after {max_wait_seconds} seconds")
        return {
            "success": False,
            "error": f"Evidence not found after {max_wait_seconds} seconds",
            "wait_time_seconds": max_wait_seconds
        }
    
    async def verify_chain_integrity(self, alert_id: str, incident_id: str, 
                                     evidence_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify the complete chain: alert -> incident -> evidence.
        
        Args:
            alert_id: Alert identifier
            incident_id: Incident identifier
            evidence_id: Optional evidence identifier
            
        Returns:
            Chain integrity verification result
        """
        results = {
            "alert_exists": False,
            "incident_exists": False,
            "evidence_exists": False,
            "chain_complete": False
        }
        
        try:
            # Check alert
            alert_result = await self.verify_alert_in_db(alert_id, max_wait_seconds=10)
            results["alert_exists"] = alert_result.get("success", False)
            
            # Check incident
            incident_result = await self.verify_incident_created(incident_id, max_wait_seconds=10)
            results["incident_exists"] = incident_result.get("success", False)
            
            # Check evidence if provided
            if evidence_id:
                with self.get_session() as session:
                    evidence_result = session.execute(
                        text("SELECT evidence_id FROM evidence_ledger WHERE evidence_id = :evidence_id"),
                        {"evidence_id": evidence_id}
                    ).fetchone()
                    results["evidence_exists"] = evidence_result is not None
            
            # Chain is complete if all required components exist
            results["chain_complete"] = (
                results["alert_exists"] and 
                results["incident_exists"] and
                (not evidence_id or results["evidence_exists"])
            )
            
            logger.info(f"Chain integrity check: {results}")
            return results
        
        except Exception as e:
            logger.error(f"Chain integrity verification error: {e}")
            return {
                **results,
                "error": str(e)
            }

