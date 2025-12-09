# Path and File Name : /home/ransomeye/rebuild/ransomeye_hnmp_engine/storage/history_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Tracks health score trends over time with daily snapshots

import os
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class ScoreSnapshot(Base):
    """SQLAlchemy model for daily health score snapshots."""
    __tablename__ = 'hnmp_score_snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    host_id = Column(String(255), nullable=False, index=True)
    snapshot_date = Column(DateTime, nullable=False, index=True)  # Date at midnight UTC
    score = Column(Float, nullable=False)
    base_score = Column(Float, nullable=True)
    risk_factor = Column(Float, nullable=True)
    num_failed_critical = Column(Integer, nullable=False, default=0)
    num_failed_high = Column(Integer, nullable=False, default=0)
    num_failed_medium = Column(Integer, nullable=False, default=0)
    num_failed_low = Column(Integer, nullable=False, default=0)
    metadata_json = Column(Text, nullable=True)  # Additional metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class HistoryStore:
    """
    Persistence layer for health score history and trends.
    """
    
    def __init__(self):
        """Initialize history store."""
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
            logger.info("History store database initialized")
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
    
    def save_daily_snapshot(self, host_id: str, score: float, base_score: float = None,
                           risk_factor: float = None, failed_counts: dict = None,
                           metadata: dict = None):
        """
        Save daily snapshot of health score.
        
        Args:
            host_id: Host identifier
            score: Health score
            base_score: Base score before ML adjustment
            risk_factor: ML predicted risk factor
            failed_counts: Dict with failure counts by severity
            metadata: Additional metadata
        """
        with self.get_session() as session:
            # Get today's date at midnight UTC
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Check if snapshot already exists for today
            existing = session.query(ScoreSnapshot).filter_by(
                host_id=host_id,
                snapshot_date=today
            ).first()
            
            if existing:
                # Update existing snapshot
                existing.score = score
                existing.base_score = base_score
                existing.risk_factor = risk_factor
                existing.num_failed_critical = failed_counts.get('critical', 0) if failed_counts else 0
                existing.num_failed_high = failed_counts.get('high', 0) if failed_counts else 0
                existing.num_failed_medium = failed_counts.get('medium', 0) if failed_counts else 0
                existing.num_failed_low = failed_counts.get('low', 0) if failed_counts else 0
                existing.metadata_json = json.dumps(metadata) if metadata else None
            else:
                # Create new snapshot
                snapshot = ScoreSnapshot(
                    host_id=host_id,
                    snapshot_date=today,
                    score=score,
                    base_score=base_score,
                    risk_factor=risk_factor,
                    num_failed_critical=failed_counts.get('critical', 0) if failed_counts else 0,
                    num_failed_high=failed_counts.get('high', 0) if failed_counts else 0,
                    num_failed_medium=failed_counts.get('medium', 0) if failed_counts else 0,
                    num_failed_low=failed_counts.get('low', 0) if failed_counts else 0,
                    metadata_json=json.dumps(metadata) if metadata else None,
                    created_at=datetime.utcnow()
                )
                session.add(snapshot)
            
            logger.debug(f"Saved daily snapshot for host: {host_id}, date: {today.date()}")
    
    def get_score_history(self, host_id: str, days: int = 30) -> list:
        """
        Get score history for a host.
        
        Args:
            host_id: Host identifier
            days: Number of days to retrieve
            
        Returns:
            List of snapshot dictionaries
        """
        with self.get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            snapshots = session.query(ScoreSnapshot).filter(
                ScoreSnapshot.host_id == host_id,
                ScoreSnapshot.snapshot_date >= cutoff_date
            ).order_by(ScoreSnapshot.snapshot_date.asc()).all()
            
            return [
                {
                    'id': s.id,
                    'host_id': s.host_id,
                    'snapshot_date': s.snapshot_date.isoformat() if s.snapshot_date else None,
                    'score': s.score,
                    'base_score': s.base_score,
                    'risk_factor': s.risk_factor,
                    'num_failed_critical': s.num_failed_critical,
                    'num_failed_high': s.num_failed_high,
                    'num_failed_medium': s.num_failed_medium,
                    'num_failed_low': s.num_failed_low,
                    'metadata': json.loads(s.metadata_json) if s.metadata_json else None
                }
                for s in snapshots
            ]
    
    def get_fleet_trend(self, days: int = 30) -> dict:
        """
        Get fleet-wide score trends.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with trend data
        """
        with self.get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            snapshots = session.query(ScoreSnapshot).filter(
                ScoreSnapshot.snapshot_date >= cutoff_date
            ).order_by(ScoreSnapshot.snapshot_date.asc()).all()
            
            # Group by date
            by_date = {}
            for s in snapshots:
                date_key = s.snapshot_date.date().isoformat()
                if date_key not in by_date:
                    by_date[date_key] = []
                by_date[date_key].append(s.score)
            
            # Calculate averages per day
            trend = []
            for date_key in sorted(by_date.keys()):
                scores = by_date[date_key]
                trend.append({
                    'date': date_key,
                    'average_score': sum(scores) / len(scores) if scores else 0.0,
                    'host_count': len(scores)
                })
            
            return {
                'days': days,
                'trend': trend
            }
    
    def cleanup_old_snapshots(self, days_to_keep: int = 365):
        """
        Clean up snapshots older than specified days.
        
        Args:
            days_to_keep: Number of days to retain
        """
        with self.get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            deleted = session.query(ScoreSnapshot).filter(
                ScoreSnapshot.snapshot_date < cutoff_date
            ).delete()
            
            logger.info(f"Cleaned up {deleted} old snapshots")

