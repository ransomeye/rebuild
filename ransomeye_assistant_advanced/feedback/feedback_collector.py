# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant_advanced/feedback/feedback_collector.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Feedback collector that stores accepted/rejected playbook suggestions

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, Text
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    from contextlib import contextmanager
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    logging.warning("SQLAlchemy not available - feedback stored to files only")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if SQLALCHEMY_AVAILABLE:
    Base = declarative_base()
    
    class FeedbackRecord(Base):
        """SQLAlchemy model for feedback table."""
        __tablename__ = 'assistant_feedback'
        
        id = Column(Integer, primary_key=True, autoincrement=True)
        artifact_id = Column(String(255), nullable=False, index=True)
        playbook_id = Column(Integer, nullable=False)
        accepted = Column(Boolean, nullable=False)
        comment = Column(Text, nullable=True)
        created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class FeedbackCollector:
    """Feedback collector for playbook suggestions."""
    
    def __init__(self):
        """Initialize feedback collector."""
        self.engine = None
        self.SessionLocal = None
        self.feedback_dir = Path(os.environ.get('FEEDBACK_DIR', '/var/lib/ransomeye/assistant_advanced/feedback'))
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
        
        if SQLALCHEMY_AVAILABLE:
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
            
            # Create table if it doesn't exist
            Base.metadata.create_all(bind=self.engine)
            logger.info("Feedback collector database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize feedback database: {e}")
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
    
    def record_feedback(self, artifact_id: str, playbook_id: int, accepted: bool, comment: Optional[str] = None):
        """
        Record feedback on playbook suggestion.
        
        Args:
            artifact_id: Artifact identifier
            playbook_id: Suggested playbook ID
            accepted: Whether suggestion was accepted
            comment: Optional comment
        """
        # Store in database
        if self.SessionLocal:
            try:
                with self.get_session() as session:
                    if session:
                        record = FeedbackRecord(
                            artifact_id=artifact_id,
                            playbook_id=playbook_id,
                            accepted=accepted,
                            comment=comment,
                            created_at=datetime.utcnow()
                        )
                        session.add(record)
                        logger.info(f"Recorded feedback: artifact={artifact_id}, playbook={playbook_id}, accepted={accepted}")
            except Exception as e:
                logger.error(f"Error recording feedback in database: {e}")
        
        # Also store as JSON file for training
        feedback_file = self.feedback_dir / f"{artifact_id}_{playbook_id}_{datetime.utcnow().timestamp()}.json"
        try:
            with open(feedback_file, 'w') as f:
                json.dump({
                    'artifact_id': artifact_id,
                    'playbook_id': playbook_id,
                    'accepted': accepted,
                    'comment': comment,
                    'timestamp': datetime.utcnow().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving feedback file: {e}")

