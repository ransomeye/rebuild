# Path and File Name : /home/ransomeye/rebuild/ransomeye_db_core/schema/models_alerts.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Alert and Policy models with time-based partitioning

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
import uuid
from .base import Base


class Alerts(Base):
    """Alerts table with composite primary key and range partitioning by created_at."""
    __tablename__ = 'alerts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, nullable=False, primary_key=True, index=True)
    alert_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)  # critical, high, medium, low, info
    source = Column(String(255), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    raw_data = Column(JSONB, nullable=True)
    status = Column(String(50), nullable=False, default='open', index=True)  # open, acknowledged, resolved, false_positive
    assigned_to = Column(String(255), nullable=True, index=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional metadata
    correlation_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    killchain_phase = Column(String(50), nullable=True, index=True)
    mitre_technique = Column(String(100), nullable=True, index=True)
    confidence_score = Column(Float, nullable=True, index=True)
    
    __table_args__ = (
        CheckConstraint("severity IN ('critical', 'high', 'medium', 'low', 'info')", name='ck_alerts_severity'),
        CheckConstraint("status IN ('open', 'acknowledged', 'resolved', 'false_positive')", name='ck_alerts_status'),
        Index('ix_alerts_created_at_severity', 'created_at', 'severity'),
        Index('ix_alerts_correlation', 'correlation_id', 'created_at'),
        {
            'postgresql_partition_by': 'RANGE (created_at)',
        },
    )


class Policies(Base):
    """Security policies configuration table."""
    __tablename__ = 'policies'
    
    policy_id = Column(Integer, primary_key=True, autoincrement=True)
    policy_name = Column(String(255), nullable=False, unique=True, index=True)
    policy_type = Column(String(100), nullable=False, index=True)  # detection, response, compliance, etc.
    description = Column(Text, nullable=True)
    rule_definition = Column(JSONB, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    priority = Column(Integer, nullable=False, default=100, index=True)
    tags = Column(JSONB, nullable=True)  # Array of tag strings
    created_by = Column(String(255), nullable=True)
    updated_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_applied_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('ix_policies_type_active', 'policy_type', 'is_active'),
    )

