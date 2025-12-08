# Path and File Name : /home/ransomeye/rebuild/ransomeye_correlation/storage/incident_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Manages metadata for correlated incidents (status, assignee)

import os
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class Incident(Base):
    """SQLAlchemy model for incidents."""
    __tablename__ = 'correlation_incidents'
    
    id = Column(String(255), primary_key=True)
    node_count = Column(Integer, nullable=False)
    edge_count = Column(Integer, nullable=False)
    first_seen = Column(DateTime, nullable=False)
    last_seen = Column(DateTime, nullable=False)
    total_alerts = Column(Integer, default=0)
    entity_types_json = Column(Text, nullable=True)  # JSON array
    node_ids_json = Column(Text, nullable=True)  # JSON array
    status = Column(String(50), default='open')  # open, investigating, resolved, false_positive
    assignee = Column(String(255), nullable=True)
    confidence_score = Column(String(20), nullable=True)  # Store as string for flexibility
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class IncidentStore:
    """
    Manages incident metadata.
    """
    
    def __init__(self):
        """Initialize incident store."""
        self.engine = None
        self.SessionLocal = None
        self._initialize_db()
    
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
            
            # Create tables
            Base.metadata.create_all(bind=self.engine)
            logger.info("Incident store database initialized")
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
    
    def create_incident(self, incident_data: dict):
        """
        Create or update incident.
        
        Args:
            incident_data: Incident data dictionary
        """
        with self.get_session() as session:
            incident_id = incident_data.get('id')
            
            # Check if exists
            existing = session.query(Incident).filter_by(id=incident_id).first()
            
            if existing:
                # Update existing
                existing.node_count = incident_data.get('node_count', existing.node_count)
                existing.edge_count = incident_data.get('edge_count', existing.edge_count)
                existing.total_alerts = incident_data.get('total_alerts', existing.total_alerts)
                existing.entity_types_json = json.dumps(incident_data.get('entity_types', []))
                existing.node_ids_json = json.dumps(incident_data.get('node_ids', []))
                if incident_data.get('first_seen'):
                    try:
                        existing.first_seen = datetime.fromisoformat(incident_data['first_seen'].replace('Z', '+00:00'))
                    except:
                        pass
                if incident_data.get('last_seen'):
                    try:
                        existing.last_seen = datetime.fromisoformat(incident_data['last_seen'].replace('Z', '+00:00'))
                    except:
                        pass
            else:
                # Create new
                first_seen = datetime.utcnow()
                if incident_data.get('first_seen'):
                    try:
                        first_seen = datetime.fromisoformat(incident_data['first_seen'].replace('Z', '+00:00'))
                    except:
                        pass
                
                incident = Incident(
                    id=incident_id,
                    node_count=incident_data.get('node_count', 0),
                    edge_count=incident_data.get('edge_count', 0),
                    first_seen=first_seen,
                    last_seen=first_seen,
                    total_alerts=incident_data.get('total_alerts', 0),
                    entity_types_json=json.dumps(incident_data.get('entity_types', [])),
                    node_ids_json=json.dumps(incident_data.get('node_ids', []))
                )
                session.add(incident)
            
            logger.info(f"Stored incident: {incident_id}")
    
    def get_incident(self, incident_id: str) -> dict:
        """
        Get incident by ID.
        
        Args:
            incident_id: Incident identifier
            
        Returns:
            Incident dictionary or None
        """
        with self.get_session() as session:
            incident = session.query(Incident).filter_by(id=incident_id).first()
            
            if incident:
                return {
                    'id': incident.id,
                    'node_count': incident.node_count,
                    'edge_count': incident.edge_count,
                    'first_seen': incident.first_seen.isoformat() if incident.first_seen else None,
                    'last_seen': incident.last_seen.isoformat() if incident.last_seen else None,
                    'total_alerts': incident.total_alerts,
                    'entity_types': json.loads(incident.entity_types_json) if incident.entity_types_json else [],
                    'node_ids': json.loads(incident.node_ids_json) if incident.node_ids_json else [],
                    'status': incident.status,
                    'assignee': incident.assignee,
                    'confidence_score': incident.confidence_score
                }
            
            return None
    
    def list_incidents(self) -> list:
        """
        List all incidents.
        
        Returns:
            List of incident dictionaries
        """
        with self.get_session() as session:
            incidents = session.query(Incident).all()
            
            return [
                {
                    'id': incident.id,
                    'node_count': incident.node_count,
                    'edge_count': incident.edge_count,
                    'status': incident.status,
                    'assignee': incident.assignee,
                    'created_at': incident.created_at.isoformat() if incident.created_at else None
                }
                for incident in incidents
            ]

