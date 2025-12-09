# Path and File Name : /home/ransomeye/rebuild/ransomeye_db_core/schema/models_core.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Core database models for Users, Config, and AuditLog with partitioning support

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from .base import Base


class Users(Base):
    """User accounts table."""
    __tablename__ = 'users'
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), nullable=False, default='analyst', index=True)  # admin, analyst, viewer
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'analyst', 'viewer')", name='ck_users_role'),
    )


class Config(Base):
    """System configuration key-value store."""
    __tablename__ = 'config'
    
    config_id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), nullable=False, unique=True, index=True)
    value = Column(Text, nullable=True)
    value_type = Column(String(50), nullable=False, default='string')  # string, int, float, bool, json
    description = Column(Text, nullable=True)
    is_encrypted = Column(Boolean, nullable=False, default=False)
    updated_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    """Audit log table partitioned by month."""
    __tablename__ = 'audit_log'
    
    audit_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True)
    username = Column(String(255), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)  # create, update, delete, login, logout, etc.
    resource_type = Column(String(100), nullable=False, index=True)  # alert, incident, user, config, etc.
    resource_id = Column(String(255), nullable=True)
    details = Column(JSONB, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('ix_audit_log_created_at_user', 'created_at', 'user_id'),
        Index('ix_audit_log_resource', 'resource_type', 'resource_id'),
        {
            'postgresql_partition_by': 'RANGE (created_at)',
        },
    )

