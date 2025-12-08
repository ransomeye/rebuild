# Path and File Name : /home/ransomeye/rebuild/ransomeye_response/registry/playbook_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Filesystem storage for signed playbook bundles

import os
import shutil
import hashlib
from pathlib import Path
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlaybookStore:
    """
    Manages filesystem storage for playbook bundles.
    """
    
    def __init__(self, storage_dir: str = None):
        """
        Initialize playbook store.
        
        Args:
            storage_dir: Base directory for playbook storage
        """
        self.storage_dir = Path(storage_dir or os.environ.get(
            'PLAYBOOK_STORAGE_DIR',
            '/home/ransomeye/rebuild/ransomeye_response/storage/playbooks'
        ))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Playbook store initialized at: {self.storage_dir}")
    
    def store_bundle(self, bundle_path: Path, playbook_name: str, version: str) -> Path:
        """
        Store a playbook bundle.
        
        Args:
            bundle_path: Path to bundle file
            playbook_name: Playbook name
            version: Playbook version
            
        Returns:
            Path to stored bundle
        """
        bundle_path = Path(bundle_path)
        
        if not bundle_path.exists():
            raise FileNotFoundError(f"Bundle file not found: {bundle_path}")
        
        # Create storage path
        safe_name = playbook_name.replace('/', '_').replace('\\', '_')
        safe_version = version.replace('/', '_').replace('\\', '_')
        stored_path = self.storage_dir / f"{safe_name}_{safe_version}.tar.gz"
        
        # Copy bundle
        shutil.copy2(bundle_path, stored_path)
        
        logger.info(f"Stored playbook bundle: {stored_path}")
        return stored_path
    
    def get_bundle_path(self, playbook_name: str, version: str) -> Optional[Path]:
        """
        Get path to stored bundle.
        
        Args:
            playbook_name: Playbook name
            version: Playbook version
            
        Returns:
            Path to bundle or None if not found
        """
        safe_name = playbook_name.replace('/', '_').replace('\\', '_')
        safe_version = version.replace('/', '_').replace('\\', '_')
        bundle_path = self.storage_dir / f"{safe_name}_{safe_version}.tar.gz"
        
        return bundle_path if bundle_path.exists() else None
    
    def calculate_bundle_hash(self, bundle_path: Path) -> str:
        """
        Calculate SHA256 hash of bundle.
        
        Args:
            bundle_path: Path to bundle file
            
        Returns:
            SHA256 hash as hex string
        """
        sha256_hash = hashlib.sha256()
        with open(bundle_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def delete_bundle(self, playbook_name: str, version: str) -> bool:
        """
        Delete a stored bundle.
        
        Args:
            playbook_name: Playbook name
            version: Playbook version
            
        Returns:
            True if deleted, False otherwise
        """
        bundle_path = self.get_bundle_path(playbook_name, version)
        
        if bundle_path and bundle_path.exists():
            bundle_path.unlink()
            logger.info(f"Deleted bundle: {bundle_path}")
            return True
        
        return False

