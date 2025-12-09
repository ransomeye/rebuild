# Path and File Name : /home/ransomeye/rebuild/ransomeye_hnmp_engine/engine/inventory_manager.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Manages host inventory with upserts and last_seen tracking

import os
import uuid
from typing import Dict, Any, Optional
from ..storage.host_db import HostDB
from ..storage.history_store import HistoryStore
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InventoryManager:
    """
    Manages host inventory with upserts and tracking.
    """
    
    def __init__(self, host_db: HostDB = None, history_store: HistoryStore = None):
        """
        Initialize inventory manager.
        
        Args:
            host_db: Host database instance
            history_store: History store instance
        """
        self.host_db = host_db or HostDB()
        self.history_store = history_store or HistoryStore()
    
    def normalize_host_id(self, profile: Dict[str, Any]) -> str:
        """
        Generate or extract host ID from profile.
        
        Args:
            profile: Host profile dictionary
            
        Returns:
            Host ID string
        """
        # Try to get host_id from profile
        host_id = profile.get('host_id')
        if host_id:
            return str(host_id)
        
        # Try MAC address
        mac = profile.get('mac_address') or profile.get('mac')
        if mac:
            return str(mac)
        
        # Try IP address
        ip = profile.get('ip_address') or profile.get('ip')
        if ip:
            return str(ip)
        
        # Try hostname
        hostname = profile.get('hostname')
        if hostname:
            return str(hostname)
        
        # Generate UUID as fallback
        return str(uuid.uuid4())
    
    def upsert_host(self, profile: Dict[str, Any]) -> str:
        """
        Insert or update host profile.
        
        Args:
            profile: Host profile dictionary
            
        Returns:
            Host ID string
        """
        host_id = self.normalize_host_id(profile)
        
        # Ensure profile has required fields
        normalized_profile = profile.copy()
        if 'host_id' not in normalized_profile:
            normalized_profile['host_id'] = host_id
        if 'os_type' not in normalized_profile:
            # Try to infer from profile
            kernel_version = normalized_profile.get('kernel_version', '')
            if 'windows' in kernel_version.lower() or normalized_profile.get('os_version', '').lower().startswith('windows'):
                normalized_profile['os_type'] = 'windows'
            else:
                normalized_profile['os_type'] = 'linux'
        
        # Upsert to database
        self.host_db.upsert_host(host_id, normalized_profile)
        
        logger.debug(f"Upserted host: {host_id}")
        
        return host_id
    
    def get_host(self, host_id: str) -> Optional[Dict[str, Any]]:
        """
        Get host profile by ID.
        
        Args:
            host_id: Host identifier
            
        Returns:
            Host dictionary or None
        """
        return self.host_db.get_host(host_id)
    
    def list_hosts(self) -> list:
        """
        List all hosts.
        
        Returns:
            List of host dictionaries
        """
        return self.host_db.list_hosts()
    
    def get_host_last_seen(self, host_id: str) -> Optional[str]:
        """
        Get last seen timestamp for a host.
        
        Args:
            host_id: Host identifier
            
        Returns:
            ISO format timestamp string or None
        """
        host = self.host_db.get_host(host_id)
        if host:
            return host.get('last_seen')
        return None
    
    def save_score_snapshot(self, host_id: str, score_result: Dict[str, Any]):
        """
        Save daily snapshot of health score.
        
        Args:
            host_id: Host identifier
            score_result: Score result dictionary from HealthScorer
        """
        self.history_store.save_daily_snapshot(
            host_id=host_id,
            score=score_result['score'],
            base_score=score_result['base_score'],
            risk_factor=score_result['risk_factor'],
            failed_counts=score_result['failed_counts'],
            metadata={
                'risk_adjustment': score_result.get('risk_adjustment', 0.0)
            }
        )
    
    def get_host_history(self, host_id: str, days: int = 30) -> list:
        """
        Get score history for a host.
        
        Args:
            host_id: Host identifier
            days: Number of days to retrieve
            
        Returns:
            List of historical snapshot dictionaries
        """
        return self.history_store.get_score_history(host_id, days)

