# Path and File Name : /home/ransomeye/rebuild/ransomeye_deception/storage/config_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Database storage for currently active decoys (Location, Type, PID)

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()


class DecoyRecord(Base):
    """Database model for decoy records."""
    __tablename__ = 'deception_decoys'
    
    id = Column(String, primary_key=True)
    type = Column(String, nullable=False)  # file, service, process, host
    location = Column(String, nullable=False)
    metadata = Column(JSON, nullable=True)
    provision_result = Column(JSON, nullable=True)
    status = Column(String, nullable=False, default='active')  # active, rotated, removed
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_rotated_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConfigStore:
    """
    Storage for decoy configurations.
    """
    
    def __init__(self):
        """Initialize config store."""
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
            logger.info("Config store database initialized")
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
    
    async def create_decoy(self, decoy_data: Dict[str, Any]) -> str:
        """
        Create decoy record.
        
        Args:
            decoy_data: Decoy data dictionary
            
        Returns:
            Decoy ID
        """
        with self.get_session() as session:
            record = DecoyRecord(
                id=decoy_data['id'],
                type=decoy_data['type'],
                location=decoy_data['location'],
                metadata=decoy_data.get('metadata'),
                provision_result=decoy_data.get('provision_result'),
                status=decoy_data.get('status', 'active'),
                created_at=datetime.fromisoformat(decoy_data.get('created_at', datetime.utcnow().isoformat())),
                last_rotated_at=datetime.fromisoformat(decoy_data['last_rotated_at']) if decoy_data.get('last_rotated_at') else None
            )
            session.add(record)
            session.commit()
            return record.id
    
    async def get_decoy(self, decoy_id: str) -> Optional[Dict[str, Any]]:
        """
        Get decoy by ID.
        
        Args:
            decoy_id: Decoy ID
            
        Returns:
            Decoy data dictionary or None
        """
        with self.get_session() as session:
            record = session.query(DecoyRecord).filter(DecoyRecord.id == decoy_id).first()
            if not record:
                return None
            
            return {
                'id': record.id,
                'type': record.type,
                'location': record.location,
                'metadata': record.metadata or {},
                'provision_result': record.provision_result or {},
                'status': record.status,
                'created_at': record.created_at.isoformat(),
                'last_rotated_at': record.last_rotated_at.isoformat() if record.last_rotated_at else None,
                'updated_at': record.updated_at.isoformat()
            }
    
    async def update_decoy(self, decoy_id: str, updates: Dict[str, Any]):
        """
        Update decoy record.
        
        Args:
            decoy_id: Decoy ID
            updates: Update dictionary
        """
        with self.get_session() as session:
            record = session.query(DecoyRecord).filter(DecoyRecord.id == decoy_id).first()
            if not record:
                raise ValueError(f"Decoy {decoy_id} not found")
            
            if 'location' in updates:
                record.location = updates['location']
            if 'metadata' in updates:
                record.metadata = updates['metadata']
            if 'provision_result' in updates:
                record.provision_result = updates['provision_result']
            if 'status' in updates:
                record.status = updates['status']
            if 'last_rotated_at' in updates:
                record.last_rotated_at = datetime.fromisoformat(updates['last_rotated_at']) if updates['last_rotated_at'] else None
            
            session.commit()
    
    async def remove_decoy(self, decoy_id: str):
        """
        Remove decoy record.
        
        Args:
            decoy_id: Decoy ID
        """
        with self.get_session() as session:
            record = session.query(DecoyRecord).filter(DecoyRecord.id == decoy_id).first()
            if record:
                session.delete(record)
                session.commit()
    
    async def get_active_decoys(self) -> List[Dict[str, Any]]:
        """
        Get all active decoys.
        
        Returns:
            List of decoy data dictionaries
        """
        with self.get_session() as session:
            records = session.query(DecoyRecord).filter(DecoyRecord.status == 'active').all()
            
            return [
                {
                    'id': r.id,
                    'type': r.type,
                    'location': r.location,
                    'metadata': r.metadata or {},
                    'provision_result': r.provision_result or {},
                    'status': r.status,
                    'created_at': r.created_at.isoformat(),
                    'last_rotated_at': r.last_rotated_at.isoformat() if r.last_rotated_at else None,
                    'updated_at': r.updated_at.isoformat()
                }
                for r in records
            ]

