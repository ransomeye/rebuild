# Path and File Name : /home/ransomeye/rebuild/ransomeye_hnmp_engine/storage/host_db.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: PostgreSQL persistence layer for host profiles, compliance results, and health scores

import os
import json
import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class Host(Base):
    """SQLAlchemy model for host inventory."""
    __tablename__ = 'hnmp_hosts'
    
    host_id = Column(String(255), primary_key=True)
    hostname = Column(String(255), nullable=True, index=True)
    os_type = Column(String(50), nullable=False)  # linux, windows
    os_version = Column(String(255), nullable=True)
    kernel_version = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True, index=True)
    mac_address = Column(String(17), nullable=True, index=True)
    profile_json = Column(Text, nullable=True)  # Full host profile JSON
    last_seen = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    first_seen = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class ComplianceResult(Base):
    """SQLAlchemy model for compliance check results."""
    __tablename__ = 'hnmp_compliance_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    host_id = Column(String(255), ForeignKey('hnmp_hosts.host_id'), nullable=False, index=True)
    rule_id = Column(String(255), nullable=False)
    rule_name = Column(String(255), nullable=False)
    severity = Column(String(20), nullable=False)  # critical, high, medium, low
    passed = Column(Boolean, nullable=False, default=False)
    actual_value = Column(Text, nullable=True)
    expected_value = Column(Text, nullable=True)
    message = Column(Text, nullable=True)
    checked_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    host = relationship("Host", backref="compliance_results")

class HealthScore(Base):
    """SQLAlchemy model for health scores."""
    __tablename__ = 'hnmp_health_scores'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    host_id = Column(String(255), ForeignKey('hnmp_hosts.host_id'), nullable=False, index=True)
    score = Column(Float, nullable=False)  # 0.0 - 100.0
    base_score = Column(Float, nullable=True)  # Before ML adjustment
    risk_factor = Column(Float, nullable=True)  # ML predicted risk (0.0 - 1.0)
    num_failed_critical = Column(Integer, nullable=False, default=0)
    num_failed_high = Column(Integer, nullable=False, default=0)
    num_failed_medium = Column(Integer, nullable=False, default=0)
    num_failed_low = Column(Integer, nullable=False, default=0)
    shap_explanation_json = Column(Text, nullable=True)  # SHAP explanation JSON
    calculated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    host = relationship("Host", backref="health_scores")

class HostDB:
    """
    Persistence layer for host profiles, compliance results, and health scores.
    """
    
    def __init__(self):
        """Initialize host database."""
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
            logger.info("Host database initialized")
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
    
    def upsert_host(self, host_id: str, profile: dict):
        """
        Insert or update host profile.
        
        Args:
            host_id: Unique host identifier
            profile: Host profile dictionary (OS, packages, sysctl, services, etc.)
        """
        with self.get_session() as session:
            existing = session.query(Host).filter_by(host_id=host_id).first()
            
            now = datetime.utcnow()
            
            if existing:
                # Update existing
                existing.hostname = profile.get('hostname', existing.hostname)
                existing.os_type = profile.get('os_type', existing.os_type)
                existing.os_version = profile.get('os_version', existing.os_version)
                existing.kernel_version = profile.get('kernel_version', existing.kernel_version)
                existing.ip_address = profile.get('ip_address', existing.ip_address)
                existing.mac_address = profile.get('mac_address', existing.mac_address)
                existing.profile_json = json.dumps(profile)
                existing.last_seen = now
                existing.updated_at = now
            else:
                # Create new
                host = Host(
                    host_id=host_id,
                    hostname=profile.get('hostname', ''),
                    os_type=profile.get('os_type', 'unknown'),
                    os_version=profile.get('os_version', ''),
                    kernel_version=profile.get('kernel_version', ''),
                    ip_address=profile.get('ip_address', ''),
                    mac_address=profile.get('mac_address', ''),
                    profile_json=json.dumps(profile),
                    first_seen=now,
                    last_seen=now,
                    created_at=now,
                    updated_at=now
                )
                session.add(host)
            
            logger.debug(f"Upserted host: {host_id}")
    
    def get_host(self, host_id: str) -> dict:
        """
        Get host profile by ID.
        
        Args:
            host_id: Host identifier
            
        Returns:
            Host dictionary or None
        """
        with self.get_session() as session:
            host = session.query(Host).filter_by(host_id=host_id).first()
            
            if host:
                profile = json.loads(host.profile_json) if host.profile_json else {}
                return {
                    'host_id': host.host_id,
                    'hostname': host.hostname,
                    'os_type': host.os_type,
                    'os_version': host.os_version,
                    'kernel_version': host.kernel_version,
                    'ip_address': host.ip_address,
                    'mac_address': host.mac_address,
                    'profile': profile,
                    'first_seen': host.first_seen.isoformat() if host.first_seen else None,
                    'last_seen': host.last_seen.isoformat() if host.last_seen else None
                }
            
            return None
    
    def save_compliance_results(self, host_id: str, results: list):
        """
        Save compliance check results.
        
        Args:
            host_id: Host identifier
            results: List of compliance result dictionaries
        """
        with self.get_session() as session:
            now = datetime.utcnow()
            
            for result in results:
                comp_result = ComplianceResult(
                    host_id=host_id,
                    rule_id=result.get('rule_id', ''),
                    rule_name=result.get('rule_name', ''),
                    severity=result.get('severity', 'low'),
                    passed=result.get('passed', False),
                    actual_value=result.get('actual_value'),
                    expected_value=result.get('expected_value'),
                    message=result.get('message'),
                    checked_at=now
                )
                session.add(comp_result)
            
            logger.debug(f"Saved {len(results)} compliance results for host: {host_id}")
    
    def get_compliance_results(self, host_id: str) -> list:
        """
        Get compliance results for a host.
        
        Args:
            host_id: Host identifier
            
        Returns:
            List of compliance result dictionaries
        """
        with self.get_session() as session:
            results = session.query(ComplianceResult).filter_by(host_id=host_id).order_by(ComplianceResult.checked_at.desc()).all()
            
            return [
                {
                    'id': r.id,
                    'host_id': r.host_id,
                    'rule_id': r.rule_id,
                    'rule_name': r.rule_name,
                    'severity': r.severity,
                    'passed': r.passed,
                    'actual_value': r.actual_value,
                    'expected_value': r.expected_value,
                    'message': r.message,
                    'checked_at': r.checked_at.isoformat() if r.checked_at else None
                }
                for r in results
            ]
    
    def save_health_score(self, host_id: str, score: float, base_score: float = None,
                         risk_factor: float = None, failed_counts: dict = None,
                         shap_explanation: dict = None):
        """
        Save health score.
        
        Args:
            host_id: Host identifier
            score: Final health score (0.0 - 100.0)
            base_score: Base score before ML adjustment
            risk_factor: ML predicted risk factor (0.0 - 1.0)
            failed_counts: Dict with keys: critical, high, medium, low
            shap_explanation: SHAP explanation dictionary
        """
        with self.get_session() as session:
            now = datetime.utcnow()
            
            health_score = HealthScore(
                host_id=host_id,
                score=score,
                base_score=base_score,
                risk_factor=risk_factor,
                num_failed_critical=failed_counts.get('critical', 0) if failed_counts else 0,
                num_failed_high=failed_counts.get('high', 0) if failed_counts else 0,
                num_failed_medium=failed_counts.get('medium', 0) if failed_counts else 0,
                num_failed_low=failed_counts.get('low', 0) if failed_counts else 0,
                shap_explanation_json=json.dumps(shap_explanation) if shap_explanation else None,
                calculated_at=now
            )
            session.add(health_score)
            
            logger.debug(f"Saved health score {score} for host: {host_id}")
    
    def get_latest_health_score(self, host_id: str) -> dict:
        """
        Get latest health score for a host.
        
        Args:
            host_id: Host identifier
            
        Returns:
            Health score dictionary or None
        """
        with self.get_session() as session:
            score = session.query(HealthScore).filter_by(host_id=host_id).order_by(HealthScore.calculated_at.desc()).first()
            
            if score:
                return {
                    'id': score.id,
                    'host_id': score.host_id,
                    'score': score.score,
                    'base_score': score.base_score,
                    'risk_factor': score.risk_factor,
                    'num_failed_critical': score.num_failed_critical,
                    'num_failed_high': score.num_failed_high,
                    'num_failed_medium': score.num_failed_medium,
                    'num_failed_low': score.num_failed_low,
                    'shap_explanation': json.loads(score.shap_explanation_json) if score.shap_explanation_json else None,
                    'calculated_at': score.calculated_at.isoformat() if score.calculated_at else None
                }
            
            return None
    
    def list_hosts(self) -> list:
        """
        List all hosts.
        
        Returns:
            List of host dictionaries
        """
        with self.get_session() as session:
            hosts = session.query(Host).all()
            
            return [
                {
                    'host_id': h.host_id,
                    'hostname': h.hostname,
                    'os_type': h.os_type,
                    'os_version': h.os_version,
                    'kernel_version': h.kernel_version,
                    'ip_address': h.ip_address,
                    'mac_address': h.mac_address,
                    'last_seen': h.last_seen.isoformat() if h.last_seen else None,
                    'first_seen': h.first_seen.isoformat() if h.first_seen else None
                }
                for h in hosts
            ]
    
    def get_fleet_stats(self) -> dict:
        """
        Get fleet-wide statistics.
        
        Returns:
            Statistics dictionary
        """
        with self.get_session() as session:
            total_hosts = session.query(Host).count()
            
            # Get average health score
            scores = session.query(HealthScore.score).join(Host).all()
            avg_score = sum(s[0] for s in scores) / len(scores) if scores else 0.0
            
            # Count by OS type
            linux_hosts = session.query(Host).filter_by(os_type='linux').count()
            windows_hosts = session.query(Host).filter_by(os_type='windows').count()
            
            # Count failed compliance checks
            failed_critical = session.query(ComplianceResult).filter_by(severity='critical', passed=False).count()
            failed_high = session.query(ComplianceResult).filter_by(severity='high', passed=False).count()
            
            return {
                'total_hosts': total_hosts,
                'linux_hosts': linux_hosts,
                'windows_hosts': windows_hosts,
                'average_health_score': round(avg_score, 2),
                'failed_critical_checks': failed_critical,
                'failed_high_checks': failed_high
            }

