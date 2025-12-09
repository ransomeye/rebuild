# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant_advanced/storage/provenance.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Provenance tracker that links summaries to source artifacts in database

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    from contextlib import contextmanager
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    logging.warning("SQLAlchemy not available - provenance tracking disabled")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if SQLALCHEMY_AVAILABLE:
    Base = declarative_base()
    
    class ProvenanceRecord(Base):
        """SQLAlchemy model for provenance table."""
        __tablename__ = 'provenance'
        
        id = Column(Integer, primary_key=True, autoincrement=True)
        artifact_id = Column(String(255), nullable=False, index=True)
        incident_id = Column(String(255), nullable=True, index=True)
        summary = Column(Text, nullable=True)
        created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class ProvenanceTracker:
    """Provenance tracker for linking artifacts to incidents."""
    
    def __init__(self):
        """Initialize provenance tracker."""
        self.engine = None
        self.SessionLocal = None
        
        if SQLALCHEMY_AVAILABLE:
            self._initialize_db()
        else:
            logger.warning("SQLAlchemy not available - provenance tracking disabled")
    
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
            
            # Create table if it doesn't exist
            Base.metadata.create_all(bind=self.engine)
            logger.info("Provenance tracker database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize provenance database: {e}")
            self.engine = None
    
    @contextmanager
    def get_session(self):
        """Context manager for database sessions."""
        if not self.SessionLocal:
            yield None
            return
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def link_artifact_to_incident(self, artifact_id: str, incident_id: str, summary: str = None):
        """
        Link artifact to incident.
        
        Args:
            artifact_id: Artifact identifier
            incident_id: Incident identifier
            summary: Optional summary text
        """
        if not self.SessionLocal:
            logger.warning("Database not available - cannot track provenance")
            return
        
        try:
            with self.get_session() as session:
                if session:
                    record = ProvenanceRecord(
                        artifact_id=artifact_id,
                        incident_id=incident_id,
                        summary=summary,
                        created_at=datetime.utcnow()
                    )
                    session.add(record)
                    logger.info(f"Linked artifact {artifact_id} to incident {incident_id}")
        except Exception as e:
            logger.error(f"Error linking artifact to incident: {e}")
    
    def get_artifacts_for_incident(self, incident_id: str) -> list:
        """
        Get all artifacts linked to an incident.
        
        Args:
            incident_id: Incident identifier
            
        Returns:
            List of artifact IDs
        """
        if not self.SessionLocal:
            return []
        
        try:
            with self.get_session() as session:
                if session:
                    records = session.query(ProvenanceRecord).filter_by(incident_id=incident_id).all()
                    return [r.artifact_id for r in records]
        except Exception as e:
            logger.error(f"Error getting artifacts for incident: {e}")
            return []

