# Path and File Name : /home/ransomeye/rebuild/ransomeye_net_scanner/storage/asset_db.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Persistence for inventory using PostgreSQL

import os
import json
import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class Asset(Base):
    """SQLAlchemy model for assets."""
    __tablename__ = 'network_assets'
    
    id = Column(String(255), primary_key=True)
    mac = Column(String(17), nullable=True, index=True)
    ip = Column(String(45), nullable=True, index=True)  # Supports IPv6
    hostname = Column(String(255), nullable=True)
    vendor = Column(String(255), nullable=True)
    asset_type = Column(String(50), nullable=True)  # PC, Server, Router
    services_json = Column(Text, nullable=True)  # JSON array
    vulnerabilities_json = Column(Text, nullable=True)  # JSON array
    source = Column(String(50), nullable=True)  # active_scan, passive, both
    first_seen = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(Text, nullable=True)

class AssetDB:
    """
    Persistence layer for network assets.
    """
    
    def __init__(self):
        """Initialize asset database."""
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
            logger.info("Asset database initialized")
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
    
    def upsert_asset(self, asset_data: dict):
        """
        Insert or update asset.
        
        Args:
            asset_data: Asset data dictionary
        """
        with self.get_session() as session:
            # Determine asset ID (prefer MAC, then IP)
            asset_id = asset_data.get('id')
            if not asset_id:
                asset_id = asset_data.get('mac') or asset_data.get('ip') or str(uuid.uuid4())
            
            # Check if exists
            existing = session.query(Asset).filter_by(id=asset_id).first()
            
            if existing:
                # Update existing
                existing.ip = asset_data.get('ip', existing.ip)
                existing.hostname = asset_data.get('hostname', existing.hostname)
                existing.vendor = asset_data.get('vendor', existing.vendor)
                existing.services_json = json.dumps(asset_data.get('services', []))
                existing.vulnerabilities_json = json.dumps(asset_data.get('vulnerabilities', []))
                existing.source = asset_data.get('source', existing.source)
                existing.last_seen = datetime.utcnow()
            else:
                # Create new
                asset = Asset(
                    id=asset_id,
                    mac=asset_data.get('mac', ''),
                    ip=asset_data.get('ip', ''),
                    hostname=asset_data.get('hostname', ''),
                    vendor=asset_data.get('vendor', ''),
                    asset_type=asset_data.get('type', 'Unknown'),
                    services_json=json.dumps(asset_data.get('services', [])),
                    vulnerabilities_json=json.dumps(asset_data.get('vulnerabilities', [])),
                    source=asset_data.get('source', 'unknown'),
                    first_seen=datetime.fromisoformat(asset_data.get('first_seen', datetime.utcnow().isoformat())) if asset_data.get('first_seen') else datetime.utcnow(),
                    last_seen=datetime.utcnow()
                )
                session.add(asset)
            
            logger.debug(f"Upserted asset: {asset_id}")
    
    def get_asset(self, asset_id: str) -> dict:
        """
        Get asset by ID.
        
        Args:
            asset_id: Asset identifier
            
        Returns:
            Asset dictionary or None
        """
        with self.get_session() as session:
            asset = session.query(Asset).filter_by(id=asset_id).first()
            
            if asset:
                return {
                    'id': asset.id,
                    'mac': asset.mac,
                    'ip': asset.ip,
                    'hostname': asset.hostname,
                    'vendor': asset.vendor,
                    'type': asset.asset_type,
                    'services': json.loads(asset.services_json) if asset.services_json else [],
                    'vulnerabilities': json.loads(asset.vulnerabilities_json) if asset.vulnerabilities_json else [],
                    'source': asset.source,
                    'first_seen': asset.first_seen.isoformat() if asset.first_seen else None,
                    'last_seen': asset.last_seen.isoformat() if asset.last_seen else None
                }
            
            return None
    
    def get_asset_by_mac(self, mac: str) -> dict:
        """
        Get asset by MAC address.
        
        Args:
            mac: MAC address
            
        Returns:
            Asset dictionary or None
        """
        with self.get_session() as session:
            asset = session.query(Asset).filter_by(mac=mac).first()
            
            if asset:
                return {
                    'id': asset.id,
                    'mac': asset.mac,
                    'ip': asset.ip,
                    'hostname': asset.hostname,
                    'vendor': asset.vendor,
                    'type': asset.asset_type,
                    'services': json.loads(asset.services_json) if asset.services_json else [],
                    'vulnerabilities': json.loads(asset.vulnerabilities_json) if asset.vulnerabilities_json else [],
                    'source': asset.source
                }
            
            return None
    
    def list_assets(self) -> list:
        """
        List all assets.
        
        Returns:
            List of asset dictionaries
        """
        with self.get_session() as session:
            assets = session.query(Asset).all()
            
            return [
                {
                    'id': asset.id,
                    'mac': asset.mac,
                    'ip': asset.ip,
                    'hostname': asset.hostname,
                    'vendor': asset.vendor,
                    'type': asset.asset_type,
                    'services': json.loads(asset.services_json) if asset.services_json else [],
                    'vulnerabilities': json.loads(asset.vulnerabilities_json) if asset.vulnerabilities_json else [],
                    'source': asset.source,
                    'first_seen': asset.first_seen.isoformat() if asset.first_seen else None,
                    'last_seen': asset.last_seen.isoformat() if asset.last_seen else None
                }
                for asset in assets
            ]
    
    def get_stats(self) -> dict:
        """
        Get asset statistics.
        
        Returns:
            Statistics dictionary
        """
        with self.get_session() as session:
            total_assets = session.query(Asset).count()
            total_vulnerabilities = 0
            
            assets = session.query(Asset).all()
            for asset in assets:
                if asset.vulnerabilities_json:
                    vulns = json.loads(asset.vulnerabilities_json)
                    total_vulnerabilities += len(vulns)
            
            return {
                'total_assets': total_assets,
                'total_vulnerabilities': total_vulnerabilities
            }

