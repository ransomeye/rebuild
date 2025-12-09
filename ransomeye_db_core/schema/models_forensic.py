# Path and File Name : /home/ransomeye/rebuild/ransomeye_db_core/schema/models_forensic.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Forensic evidence models with encrypted filepath fields

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, LargeBinary, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
import uuid
from .base import Base


class EvidenceLedger(Base):
    """Forensic evidence ledger with chain of custody tracking."""
    __tablename__ = 'evidence_ledger'
    
    evidence_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    evidence_type = Column(String(100), nullable=False, index=True)  # memory, disk, network, log, etc.
    source_host = Column(String(255), nullable=True, index=True)
    source_path = Column(Text, nullable=True)  # Original path (encrypted)
    stored_path = Column(Text, nullable=False)  # Storage path (encrypted)
    file_hash_md5 = Column(String(32), nullable=True, index=True)
    file_hash_sha256 = Column(String(64), nullable=False, index=True)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    metadata = Column(JSONB, nullable=True)
    
    # Chain of custody
    collected_by = Column(String(255), nullable=False)
    collected_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    verified_by = Column(String(255), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    verification_hash = Column(String(64), nullable=True)
    
    # Status
    is_encrypted = Column(Boolean, nullable=False, default=True)
    is_compressed = Column(Boolean, nullable=False, default=False)
    retention_until = Column(DateTime, nullable=True, index=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_evidence_incident_type', 'incident_id', 'evidence_type'),
        Index('ix_evidence_collected_at', 'collected_at', 'evidence_type'),
    )


class Artifacts(Base):
    """Forensic artifacts extracted from evidence."""
    __tablename__ = 'artifacts'
    
    artifact_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    artifact_type = Column(String(100), nullable=False, index=True)  # process, file, registry, network, etc.
    artifact_name = Column(String(500), nullable=False)
    filepath = Column(Text, nullable=True)  # Encrypted field
    content_preview = Column(Text, nullable=True)  # First 1000 chars
    full_content = Column(LargeBinary, nullable=True)  # For small artifacts
    metadata = Column(JSONB, nullable=True)
    
    # Extraction metadata
    extracted_by = Column(String(255), nullable=False)
    extracted_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    extraction_method = Column(String(100), nullable=True)
    
    # Classification
    classification = Column(String(50), nullable=True, index=True)  # benign, suspicious, malicious, unknown
    yara_matches = Column(JSONB, nullable=True)  # Array of YARA rule matches
    malware_dna = Column(Text, nullable=True)  # Extracted DNA signature
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_artifacts_evidence_type', 'evidence_id', 'artifact_type'),
        Index('ix_artifacts_classification', 'classification', 'extracted_at'),
    )

