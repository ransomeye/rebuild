# Path and File Name : /home/ransomeye/rebuild/ransomeye_net_scanner/storage/scan_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Stores raw scan reports in PostgreSQL

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

class ScanReport(Base):
    """SQLAlchemy model for scan reports."""
    __tablename__ = 'scan_reports'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_id = Column(String(255), nullable=False, index=True)
    subnet = Column(String(50), nullable=False)
    scan_type = Column(String(50), nullable=False)  # active, passive, both
    intensity = Column(String(10), nullable=True)  # T1-T5
    report_json = Column(Text, nullable=False)  # Full scan result JSON
    status = Column(String(50), nullable=False)  # started, completed, error
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class ScanStore:
    """
    Persistence layer for scan reports.
    """
    
    def __init__(self):
        """Initialize scan store."""
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
            logger.info("Scan store database initialized")
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
    
    def save_scan(self, scan_id: str, subnet: str, scan_result: dict):
        """
        Save scan report.
        
        Args:
            scan_id: Scan identifier
            subnet: Scanned subnet
            scan_result: Scan result dictionary
        """
        with self.get_session() as session:
            report = ScanReport(
                scan_id=scan_id,
                subnet=subnet,
                scan_type=scan_result.get('scan_type', 'active'),
                intensity=scan_result.get('intensity', ''),
                report_json=json.dumps(scan_result),
                status=scan_result.get('status', 'completed'),
                completed_at=datetime.utcnow()
            )
            session.add(report)
            
            logger.debug(f"Saved scan report: {scan_id} for {subnet}")
    
    def list_scans(self) -> list:
        """
        List all scans.
        
        Returns:
            List of scan dictionaries
        """
        with self.get_session() as session:
            scans = session.query(ScanReport).order_by(ScanReport.created_at.desc()).limit(100).all()
            
            return [
                {
                    'scan_id': scan.scan_id,
                    'subnet': scan.subnet,
                    'scan_type': scan.scan_type,
                    'status': scan.status,
                    'created_at': scan.created_at.isoformat() if scan.created_at else None,
                    'completed_at': scan.completed_at.isoformat() if scan.completed_at else None
                }
                for scan in scans
            ]

