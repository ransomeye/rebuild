# Path and File Name : /home/ransomeye/rebuild/ransomeye_response/registry/playbook_registry.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Database interactions for playbooks table using SQLAlchemy

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class PlaybookRecord(Base):
    """SQLAlchemy model for playbooks table."""
    __tablename__ = 'playbooks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    risk_level = Column(String(20), nullable=False)  # low, medium, high, critical
    approved_by = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)
    bundle_path = Column(String(512), nullable=False)
    manifest_hash = Column(String(64), nullable=True)  # SHA256 of manifest
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(Text, nullable=True)  # JSON metadata
    
    def to_dict(self):
        """Convert playbook record to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'risk_level': self.risk_level,
            'approved_by': self.approved_by,
            'is_active': self.is_active,
            'bundle_path': self.bundle_path,
            'manifest_hash': self.manifest_hash,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'metadata': self.metadata_json
        }

class PlaybookRegistry:
    """Database interface for playbook registry."""
    
    def __init__(self):
        """Initialize playbook registry with database connection."""
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
            logger.info("Playbook registry database initialized")
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
    
    def register_playbook(self, name: str, version: str, risk_level: str,
                         bundle_path: str, manifest_hash: str = None,
                         metadata: dict = None) -> int:
        """
        Register a new playbook.
        
        Args:
            name: Playbook name
            version: Playbook version
            risk_level: Risk level (low, medium, high, critical)
            bundle_path: Path to playbook bundle
            manifest_hash: SHA256 hash of manifest
            metadata: Optional metadata dictionary
            
        Returns:
            Playbook ID
        """
        import json
        
        with self.get_session() as session:
            # Check if playbook already exists
            existing = session.query(PlaybookRecord).filter_by(
                name=name, version=version
            ).first()
            
            if existing:
                # Update existing
                existing.bundle_path = bundle_path
                existing.manifest_hash = manifest_hash
                existing.risk_level = risk_level
                existing.metadata_json = json.dumps(metadata) if metadata else None
                existing.updated_at = datetime.utcnow()
                playbook_id = existing.id
                logger.info(f"Updated playbook: {name} v{version}")
            else:
                # Create new
                playbook = PlaybookRecord(
                    name=name,
                    version=version,
                    risk_level=risk_level,
                    bundle_path=bundle_path,
                    manifest_hash=manifest_hash,
                    metadata_json=json.dumps(metadata) if metadata else None,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(playbook)
                session.flush()
                playbook_id = playbook.id
                logger.info(f"Registered playbook: {name} v{version}")
            
            return playbook_id
    
    def get_playbook(self, playbook_id: int) -> dict:
        """
        Get playbook by ID.
        
        Args:
            playbook_id: Playbook identifier
            
        Returns:
            Playbook dictionary or None
        """
        with self.get_session() as session:
            record = session.query(PlaybookRecord).filter_by(id=playbook_id).first()
            if record:
                return record.to_dict()
            return None
    
    def get_playbook_by_name_version(self, name: str, version: str) -> dict:
        """
        Get playbook by name and version.
        
        Args:
            name: Playbook name
            version: Playbook version
            
        Returns:
            Playbook dictionary or None
        """
        with self.get_session() as session:
            record = session.query(PlaybookRecord).filter_by(
                name=name, version=version
            ).first()
            if record:
                return record.to_dict()
            return None
    
    def list_playbooks(self, active_only: bool = False, limit: int = 100) -> list:
        """
        List all playbooks.
        
        Args:
            active_only: Only return active playbooks
            limit: Maximum number of playbooks to return
            
        Returns:
            List of playbook dictionaries
        """
        with self.get_session() as session:
            query = session.query(PlaybookRecord)
            
            if active_only:
                query = query.filter_by(is_active=True)
            
            records = query.order_by(PlaybookRecord.created_at.desc()).limit(limit).all()
            
            return [record.to_dict() for record in records]
    
    def approve_playbook(self, playbook_id: int, approved_by: str) -> bool:
        """
        Approve a playbook (required for high-risk playbooks).
        
        Args:
            playbook_id: Playbook identifier
            approved_by: Name of approver
            
        Returns:
            True if successful, False otherwise
        """
        with self.get_session() as session:
            record = session.query(PlaybookRecord).filter_by(id=playbook_id).first()
            if record:
                record.approved_by = approved_by
                record.is_active = True
                record.updated_at = datetime.utcnow()
                logger.info(f"Playbook {playbook_id} approved by {approved_by}")
                return True
            return False
    
    def activate_playbook(self, playbook_id: int) -> bool:
        """
        Activate a playbook.
        
        Args:
            playbook_id: Playbook identifier
            
        Returns:
            True if successful, False otherwise
        """
        with self.get_session() as session:
            record = session.query(PlaybookRecord).filter_by(id=playbook_id).first()
            if record:
                record.is_active = True
                record.updated_at = datetime.utcnow()
                logger.info(f"Playbook {playbook_id} activated")
                return True
            return False
    
    def deactivate_playbook(self, playbook_id: int) -> bool:
        """
        Deactivate a playbook.
        
        Args:
            playbook_id: Playbook identifier
            
        Returns:
            True if successful, False otherwise
        """
        with self.get_session() as session:
            record = session.query(PlaybookRecord).filter_by(id=playbook_id).first()
            if record:
                record.is_active = False
                record.updated_at = datetime.utcnow()
                logger.info(f"Playbook {playbook_id} deactivated")
                return True
            return False

