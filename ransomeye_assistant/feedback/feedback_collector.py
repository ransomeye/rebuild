# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant/feedback/feedback_collector.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Writes feedback events to disk/DB

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class FeedbackRecord(Base):
    """SQLAlchemy model for feedback table."""
    __tablename__ = 'assistant_feedback'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(String(255), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    rating = Column(String(50), nullable=True)  # thumbs_up, thumbs_down, correction
    correction = Column(Text, nullable=True)
    comment = Column(Text, nullable=True)
    sources = Column(Text, nullable=True)  # JSON
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class FeedbackCollector:
    """
    Collects and stores user feedback for model improvement.
    """
    
    def __init__(self):
        """Initialize feedback collector."""
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
            logger.info("Feedback collector database initialized")
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
    
    def log_query(self, query_id: str, question: str, answer: str,
                  sources: List[Dict[str, Any]], ranked_results: List[Dict[str, Any]]):
        """
        Log a query for feedback collection.
        
        Args:
            query_id: Query identifier
            question: User question
            answer: Generated answer
            sources: Source documents
            ranked_results: Ranked retrieval results
        """
        with self.get_session() as session:
            # Check if query already exists
            existing = session.query(FeedbackRecord).filter_by(query_id=query_id).first()
            
            if existing:
                # Update existing
                existing.question = question
                existing.answer = answer
                existing.sources = json.dumps(sources)
            else:
                # Create new
                record = FeedbackRecord(
                    query_id=query_id,
                    question=question,
                    answer=answer,
                    sources=json.dumps(sources),
                    created_at=datetime.utcnow()
                )
                session.add(record)
            
            logger.info(f"Logged query: {query_id}")
    
    def submit_feedback(self, query_id: str, rating: str, correction: Optional[str] = None,
                       comment: Optional[str] = None):
        """
        Submit user feedback.
        
        Args:
            query_id: Query identifier
            rating: Rating (thumbs_up, thumbs_down, correction)
            correction: Corrected answer (if rating is correction)
            comment: Optional comment
        """
        with self.get_session() as session:
            record = session.query(FeedbackRecord).filter_by(query_id=query_id).first()
            
            if record:
                record.rating = rating
                record.correction = correction
                record.comment = comment
                logger.info(f"Feedback submitted for query: {query_id} ({rating})")
            else:
                logger.warning(f"Query {query_id} not found for feedback")
    
    def get_feedback_data(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get feedback data for training.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of feedback records
        """
        with self.get_session() as session:
            records = session.query(FeedbackRecord).filter(
                FeedbackRecord.rating.isnot(None)
            ).limit(limit).all()
            
            feedback_data = []
            for record in records:
                feedback_data.append({
                    'query_id': record.query_id,
                    'question': record.question,
                    'answer': record.answer,
                    'rating': record.rating,
                    'correction': record.correction,
                    'sources': json.loads(record.sources) if record.sources else [],
                    'created_at': record.created_at.isoformat() if record.created_at else None
                })
            
            return feedback_data

