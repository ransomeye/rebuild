# Path and File Name : /home/ransomeye/rebuild/ransomeye_killchain/storage/timeline_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Database interface for saving and retrieving attack timelines

import os
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class TimelineRecord(Base):
    """SQLAlchemy model for timelines table."""
    __tablename__ = 'killchain_timelines'
    
    timeline_id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(String(255), nullable=False, index=True)
    timeline_json = Column(Text, nullable=False)
    graph_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert timeline record to dictionary."""
        return {
            'timeline_id': self.timeline_id,
            'incident_id': self.incident_id,
            'timeline': json.loads(self.timeline_json) if self.timeline_json else None,
            'graph': json.loads(self.graph_json) if self.graph_json else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class TimelineStore:
    """Database interface for timeline storage."""
    
    def __init__(self):
        """Initialize timeline store with database connection."""
        self.engine = None
        self.SessionLocal = None
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize database connection from environment variables."""
        db_host = os.environ.get('DB_HOST', 'localhost')
        db_port = os.environ.get('DB_PORT', '5432')
        db_name = os.environ.get('DB_NAME', 'ransomeye')
        db_user = os.environ.get('DB_USER', 'gagan')
        db_pass = os.environ.get('DB_PASS', 'gagan')
        
        connection_string = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        
        try:
            self.engine = create_engine(connection_string, pool_pre_ping=True, echo=False)
            self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
            
            # Create tables if they don't exist
            Base.metadata.create_all(bind=self.engine)
            logger.info("Timeline store database initialized")
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
    
    def save_timeline(self, incident_id: str, timeline: dict, graph: dict = None) -> int:
        """
        Save timeline to database.
        
        Args:
            incident_id: Incident identifier
            timeline: Timeline dictionary
            graph: Optional graph dictionary
            
        Returns:
            Timeline ID
        """
        with self.get_session() as session:
            # Check if timeline exists
            existing = session.query(TimelineRecord).filter_by(incident_id=incident_id).first()
            
            if existing:
                # Update existing timeline
                existing.timeline_json = json.dumps(timeline)
                existing.graph_json = json.dumps(graph) if graph else None
                existing.updated_at = datetime.utcnow()
                timeline_id = existing.timeline_id
                logger.info(f"Updated timeline for incident {incident_id}")
            else:
                # Create new timeline
                timeline_record = TimelineRecord(
                    incident_id=incident_id,
                    timeline_json=json.dumps(timeline),
                    graph_json=json.dumps(graph) if graph else None,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(timeline_record)
                session.flush()
                timeline_id = timeline_record.timeline_id
                logger.info(f"Saved timeline for incident {incident_id}")
            
            return timeline_id
    
    def get_timeline(self, incident_id: str) -> dict:
        """
        Get timeline by incident ID.
        
        Args:
            incident_id: Incident identifier
            
        Returns:
            Timeline dictionary or None
        """
        with self.get_session() as session:
            record = session.query(TimelineRecord).filter_by(incident_id=incident_id).first()
            if record:
                return record.to_dict()
            return None
    
    def list_timelines(self, limit: int = 100) -> list:
        """
        List all timelines.
        
        Args:
            limit: Maximum number of timelines to return
            
        Returns:
            List of timeline dictionaries
        """
        with self.get_session() as session:
            records = session.query(TimelineRecord).order_by(
                TimelineRecord.created_at.desc()
            ).limit(limit).all()
            
            return [record.to_dict() for record in records]

