# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_core/registry/model_registry.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: SQLAlchemy models and functions for model registry database operations

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Integer, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class ModelRecord(Base):
    """SQLAlchemy model for the models table."""
    __tablename__ = 'models'
    
    model_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default='inactive', index=True)  # active, inactive, deprecated
    sha256 = Column(String(64), nullable=False, unique=True, index=True)
    file_path = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)
    created_by = Column(String(255), nullable=True)
    
    def to_dict(self):
        """Convert model record to dictionary."""
        return {
            'model_id': self.model_id,
            'name': self.name,
            'version': self.version,
            'status': self.status,
            'sha256': self.sha256,
            'file_path': self.file_path,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'activated_at': self.activated_at.isoformat() if self.activated_at else None,
            'created_by': self.created_by
        }

class ModelRegistry:
    """Model registry manager for database operations."""
    
    def __init__(self):
        """Initialize registry with database connection."""
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
            logger.info("Model registry database initialized")
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
    
    def register_model(self, name: str, version: str, sha256: str, file_path: str, 
                       metadata_json: str = None, created_by: str = None) -> int:
        """
        Register a new model in the database.
        
        Args:
            name: Model name
            version: Model version
            sha256: SHA256 hash of the model bundle
            file_path: Path to the model file
            metadata_json: JSON string of model metadata
            created_by: User who uploaded the model
            
        Returns:
            model_id of the registered model
        """
        with self.get_session() as session:
            # Check if model with same SHA256 already exists
            existing = session.query(ModelRecord).filter_by(sha256=sha256).first()
            if existing:
                logger.warning(f"Model with SHA256 {sha256[:16]}... already exists")
                return existing.model_id
            
            # Deactivate all other models with the same name
            session.query(ModelRecord).filter_by(name=name).update({'status': 'inactive'})
            
            # Create new model record
            model_record = ModelRecord(
                name=name,
                version=version,
                status='inactive',
                sha256=sha256,
                file_path=file_path,
                metadata_json=metadata_json,
                created_by=created_by,
                uploaded_at=datetime.utcnow()
            )
            
            session.add(model_record)
            session.flush()
            model_id = model_record.model_id
            
            logger.info(f"Registered model: {name} v{version} (ID: {model_id})")
            return model_id
    
    def activate_model(self, model_id: int) -> bool:
        """
        Activate a model by ID.
        
        Args:
            model_id: ID of the model to activate
            
        Returns:
            True if activation successful, False otherwise
        """
        with self.get_session() as session:
            model = session.query(ModelRecord).filter_by(model_id=model_id).first()
            if not model:
                logger.error(f"Model ID {model_id} not found")
                return False
            
            # Deactivate all other models
            session.query(ModelRecord).update({'status': 'inactive', 'activated_at': None})
            
            # Activate this model
            model.status = 'active'
            model.activated_at = datetime.utcnow()
            
            logger.info(f"Activated model: {model.name} v{model.version} (ID: {model_id})")
            return True
    
    def get_active_model(self) -> ModelRecord:
        """
        Get the currently active model.
        
        Returns:
            ModelRecord of the active model, or None if no active model
        """
        with self.get_session() as session:
            model = session.query(ModelRecord).filter_by(status='active').first()
            return model
    
    def get_model_by_id(self, model_id: int) -> ModelRecord:
        """
        Get a model by ID.
        
        Args:
            model_id: ID of the model
            
        Returns:
            ModelRecord or None if not found
        """
        with self.get_session() as session:
            return session.query(ModelRecord).filter_by(model_id=model_id).first()
    
    def get_model_by_name(self, name: str) -> ModelRecord:
        """
        Get the latest model by name.
        
        Args:
            name: Model name
            
        Returns:
            ModelRecord or None if not found
        """
        with self.get_session() as session:
            return session.query(ModelRecord).filter_by(name=name).order_by(
                ModelRecord.uploaded_at.desc()
            ).first()
    
    def list_models(self, status: str = None) -> list:
        """
        List all models, optionally filtered by status.
        
        Args:
            status: Optional status filter (active, inactive, deprecated)
            
        Returns:
            List of ModelRecord objects
        """
        with self.get_session() as session:
            query = session.query(ModelRecord)
            if status:
                query = query.filter_by(status=status)
            return query.order_by(ModelRecord.uploaded_at.desc()).all()
    
    def delete_model(self, model_id: int) -> bool:
        """
        Delete a model record (does not delete the file).
        
        Args:
            model_id: ID of the model to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        with self.get_session() as session:
            model = session.query(ModelRecord).filter_by(model_id=model_id).first()
            if not model:
                logger.error(f"Model ID {model_id} not found")
                return False
            
            if model.status == 'active':
                logger.warning(f"Cannot delete active model: {model.name}")
                return False
            
            session.delete(model)
            logger.info(f"Deleted model record: {model.name} v{model.version} (ID: {model_id})")
            return True

# Global registry instance
_registry_instance = None

def get_registry() -> ModelRegistry:
    """Get or create the global model registry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ModelRegistry()
    return _registry_instance

