# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/schema/knowledge_graph.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: SQLAlchemy models for the Unified Threat Knowledge Graph

import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, Text, Integer, Float, ForeignKey,
    DateTime, Boolean, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class Vulnerability(Base):
    """CVE vulnerability records."""
    __tablename__ = 'vulnerabilities'
    
    cve_id = Column(String(20), primary_key=True, index=True)
    description = Column(Text, nullable=True)
    severity = Column(String(20), nullable=True)  # CRITICAL, HIGH, MEDIUM, LOW
    cvss_v3_score = Column(Float, nullable=True)
    cvss_v2_score = Column(Float, nullable=True)
    published_date = Column(DateTime, nullable=True)
    modified_date = Column(DateTime, nullable=True)
    cwe_id = Column(String(20), ForeignKey('weaknesses.cwe_id'), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    weakness = relationship("Weakness", back_populates="vulnerabilities")
    mitigations = relationship("Mitigation", back_populates="vulnerability")
    
    __table_args__ = (
        Index('idx_vuln_severity', 'severity'),
        Index('idx_vuln_published', 'published_date'),
    )


class Mitigation(Base):
    """CISA KEV mitigations and required actions."""
    __tablename__ = 'mitigations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cve_id = Column(String(20), ForeignKey('vulnerabilities.cve_id'), nullable=False, index=True)
    required_action = Column(Text, nullable=False)
    vendor_project = Column(String(255), nullable=True)
    product = Column(String(255), nullable=True)
    added_date = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    vulnerability = relationship("Vulnerability", back_populates="mitigations")
    
    __table_args__ = (
        UniqueConstraint('cve_id', 'required_action', name='uq_mitigation_cve_action'),
        Index('idx_mitigation_cve', 'cve_id'),
    )


class Weakness(Base):
    """CWE weakness records."""
    __tablename__ = 'weaknesses'
    
    cwe_id = Column(String(20), primary_key=True, index=True)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    abstraction = Column(String(50), nullable=True)  # Class, Base, Variant, etc.
    status = Column(String(50), nullable=True)  # Deprecated, Draft, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    vulnerabilities = relationship("Vulnerability", back_populates="weakness")
    attack_patterns = relationship("AttackPattern", secondary='weakness_attack_pattern', back_populates="weaknesses")
    
    __table_args__ = (
        Index('idx_weakness_name', 'name'),
    )


class AttackPattern(Base):
    """CAPEC attack pattern records."""
    __tablename__ = 'attack_patterns'
    
    capec_id = Column(String(20), primary_key=True, index=True)
    name = Column(String(500), nullable=False)
    step_by_step_logic = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    likelihood_of_attack = Column(String(50), nullable=True)
    typical_severity = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    weaknesses = relationship("Weakness", secondary='weakness_attack_pattern', back_populates="attack_patterns")
    tactics = relationship("Tactic", secondary='tactic_attack_pattern', back_populates="attack_patterns")
    
    __table_args__ = (
        Index('idx_attack_pattern_name', 'name'),
    )


class Tactic(Base):
    """MITRE ATT&CK tactics."""
    __tablename__ = 'tactics'
    
    mitre_id = Column(String(50), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    external_id = Column(String(50), nullable=True)  # T1001, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    attack_patterns = relationship("AttackPattern", secondary='tactic_attack_pattern', back_populates="tactics")
    
    __table_args__ = (
        Index('idx_tactic_name', 'name'),
        Index('idx_tactic_external_id', 'external_id'),
    )


class IOC(Base):
    """Indicators of Compromise (IPs, hashes, domains)."""
    __tablename__ = 'iocs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(String(500), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # ip, hash, domain, url
    maliciousness_score = Column(Float, default=0.0)
    malware_family = Column(String(255), nullable=True)
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    source = Column(String(100), nullable=True)  # malwarebazaar, threatfox, etc.
    tags = Column(Text, nullable=True)  # JSON array of tags
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_ioc_value', 'value'),
        Index('idx_ioc_type', 'type'),
        Index('idx_ioc_score', 'maliciousness_score'),
        UniqueConstraint('value', 'type', name='uq_ioc_value_type'),
    )


# Association tables for many-to-many relationships
from sqlalchemy import Table

weakness_attack_pattern = Table(
    'weakness_attack_pattern',
    Base.metadata,
    Column('cwe_id', String(20), ForeignKey('weaknesses.cwe_id'), primary_key=True),
    Column('capec_id', String(20), ForeignKey('attack_patterns.capec_id'), primary_key=True),
    Index('idx_wap_cwe', 'cwe_id'),
    Index('idx_wap_capec', 'capec_id'),
)

tactic_attack_pattern = Table(
    'tactic_attack_pattern',
    Base.metadata,
    Column('mitre_id', String(50), ForeignKey('tactics.mitre_id'), primary_key=True),
    Column('capec_id', String(20), ForeignKey('attack_patterns.capec_id'), primary_key=True),
    Index('idx_tap_mitre', 'mitre_id'),
    Index('idx_tap_capec', 'capec_id'),
)


def get_engine():
    """Get database engine from environment variables."""
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'ransomeye')
    db_user = os.environ.get('DB_USER', 'gagan')
    db_pass = os.environ.get('DB_PASS', 'gagan')
    
    db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    return create_engine(db_url, pool_pre_ping=True)


def create_tables():
    """Create all tables in the database."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("✓ Knowledge graph tables created")


def get_session():
    """Get database session."""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


if __name__ == "__main__":
    create_tables()

