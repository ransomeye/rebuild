# Path and File Name : /home/ransomeye/rebuild/ransomeye_alert_engine/storage/policy_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Manages storage of active/staged policy files on disk

import os
import shutil
from pathlib import Path
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PolicyStore:
    """Manages storage of policy files on disk."""
    
    def __init__(self, storage_dir: str = None):
        """
        Initialize policy store.
        
        Args:
            storage_dir: Base directory for policy storage
        """
        self.storage_dir = Path(storage_dir or os.environ.get(
            'POLICY_STORAGE_DIR',
            '/home/ransomeye/rebuild/ransomeye_alert_engine/storage/policies'
        ))
        self.active_dir = self.storage_dir / "active"
        self.staged_dir = self.storage_dir / "staged"
        self.archive_dir = self.storage_dir / "archive"
        
        # Create directories
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.active_dir.mkdir(parents=True, exist_ok=True)
        self.staged_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Policy store initialized at: {self.storage_dir}")
    
    def store_policy(self, bundle_path: Path, policy_hash: str) -> Path:
        """
        Store a policy bundle.
        
        Args:
            bundle_path: Path to policy bundle
            policy_hash: Hash of the policy
            
        Returns:
            Path to stored bundle
        """
        # Archive old active policy if exists
        active_policy = self.active_dir / "current.tar.gz"
        if active_policy.exists():
            archive_path = self.archive_dir / f"policy_{policy_hash[:16]}.tar.gz"
            shutil.copy2(active_policy, archive_path)
            logger.info(f"Archived previous policy to: {archive_path}")
        
        # Store new policy as active
        stored_path = self.active_dir / "current.tar.gz"
        shutil.copy2(bundle_path, stored_path)
        
        logger.info(f"Stored policy bundle: {stored_path}")
        return stored_path
    
    def get_active_policy_path(self) -> Optional[Path]:
        """
        Get path to active policy bundle.
        
        Returns:
            Path to active policy or None
        """
        active_path = self.active_dir / "current.tar.gz"
        if active_path.exists():
            return active_path
        return None
    
    def list_archived_policies(self) -> list:
        """
        List archived policies.
        
        Returns:
            List of archived policy paths
        """
        return list(self.archive_dir.glob("*.tar.gz"))

