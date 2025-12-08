# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant/storage/kv_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: SQLite or Postgres wrapper to store document text (FAISS only stores vectors)

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy import create_engine, Column, String, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class DocumentChunk(Base):
    """SQLAlchemy model for document chunks."""
    __tablename__ = 'document_chunks'
    
    chunk_id = Column(String(255), primary_key=True)
    doc_id = Column(String(255), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)

class KVStore:
    """
    Key-value store for document chunks (FAISS only stores vectors).
    """
    
    def __init__(self):
        """Initialize KV store."""
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
            logger.info("KV store database initialized")
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
    
    def store(self, chunk_id: str, data: Dict[str, Any]):
        """
        Store document chunk.
        
        Args:
            chunk_id: Chunk identifier
            data: Chunk data dictionary
        """
        with self.get_session() as session:
            # Check if exists
            existing = session.query(DocumentChunk).filter_by(chunk_id=chunk_id).first()
            
            if existing:
                # Update
                existing.text = data.get('text', '')
                existing.metadata_json = json.dumps(data.get('metadata', {}))
            else:
                # Create new
                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    doc_id=data.get('doc_id', ''),
                    chunk_index=data.get('chunk_index', 0),
                    text=data.get('text', ''),
                    metadata_json=json.dumps(data.get('metadata', {}))
                )
                session.add(chunk)
            
            logger.debug(f"Stored chunk: {chunk_id}")
    
    def get(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document chunk.
        
        Args:
            chunk_id: Chunk identifier
            
        Returns:
            Chunk data dictionary or None
        """
        with self.get_session() as session:
            chunk = session.query(DocumentChunk).filter_by(chunk_id=chunk_id).first()
            
            if chunk:
                return {
                    'chunk_id': chunk.chunk_id,
                    'doc_id': chunk.doc_id,
                    'chunk_index': chunk.chunk_index,
                    'text': chunk.text,
                    'metadata': json.loads(chunk.metadata_json) if chunk.metadata_json else {}
                }
            
            return None
    
    def delete(self, chunk_id: str) -> bool:
        """
        Delete document chunk.
        
        Args:
            chunk_id: Chunk identifier
            
        Returns:
            True if deleted, False otherwise
        """
        with self.get_session() as session:
            chunk = session.query(DocumentChunk).filter_by(chunk_id=chunk_id).first()
            if chunk:
                session.delete(chunk)
                logger.info(f"Deleted chunk: {chunk_id}")
                return True
            return False

