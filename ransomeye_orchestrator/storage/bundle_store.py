# Path and File Name : /home/ransomeye/rebuild/ransomeye_orchestrator/storage/bundle_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Manages completed bundle files on disk

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BundleStore:
    """Manages completed bundle files on disk."""
    
    def __init__(self, base_path: str = None):
        """
        Initialize bundle store.
        
        Args:
            base_path: Base path for bundle storage (default: OUTPUT_DIR/bundles)
        """
        if base_path is None:
            base_path = os.environ.get('OUTPUT_DIR', '/home/ransomeye/rebuild/data')
            base_path = os.path.join(base_path, 'bundles')
        
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save_bundle(self, bundle_path: Path, incident_id: str) -> Path:
        """
        Save bundle to store.
        
        Args:
            bundle_path: Path to bundle file
            incident_id: Incident identifier
        
        Returns:
            Path where bundle was saved
        """
        # Create incident directory
        incident_dir = self.base_path / incident_id
        incident_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy bundle to store
        dest_path = incident_dir / bundle_path.name
        import shutil
        shutil.copy2(bundle_path, dest_path)
        
        logger.info(f"Bundle saved to store: {dest_path}")
        return dest_path
    
    def list_bundles(self, incident_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List bundles in store.
        
        Args:
            incident_id: Optional incident ID to filter
        
        Returns:
            List of bundle information dictionaries
        """
        bundles = []
        
        if incident_id:
            search_dirs = [self.base_path / incident_id]
        else:
            search_dirs = [d for d in self.base_path.iterdir() if d.is_dir()]
        
        for dir_path in search_dirs:
            if not dir_path.exists():
                continue
            
            for bundle_file in dir_path.glob("*.tar.*"):
                stat = bundle_file.stat()
                bundles.append({
                    'path': str(bundle_file),
                    'incident_id': dir_path.name,
                    'size': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'name': bundle_file.name
                })
        
        return sorted(bundles, key=lambda x: x['created_at'], reverse=True)
    
    def get_bundle(self, incident_id: str, bundle_name: Optional[str] = None) -> Optional[Path]:
        """
        Get bundle path.
        
        Args:
            incident_id: Incident identifier
            bundle_name: Optional bundle filename (default: latest)
        
        Returns:
            Bundle path or None
        """
        incident_dir = self.base_path / incident_id
        
        if not incident_dir.exists():
            return None
        
        if bundle_name:
            bundle_path = incident_dir / bundle_name
            return bundle_path if bundle_path.exists() else None
        
        # Get latest bundle
        bundles = list(incident_dir.glob("*.tar.*"))
        if bundles:
            return max(bundles, key=lambda p: p.stat().st_mtime)
        
        return None
    
    def delete_bundle(self, incident_id: str, bundle_name: str) -> bool:
        """
        Delete bundle from store.
        
        Args:
            incident_id: Incident identifier
            bundle_name: Bundle filename
        
        Returns:
            True if deleted
        """
        bundle_path = self.base_path / incident_id / bundle_name
        
        if bundle_path.exists():
            bundle_path.unlink()
            logger.info(f"Bundle deleted: {bundle_path}")
            return True
        
        return False
    
    def cleanup_old_bundles(self, days: int = 90):
        """
        Clean up bundles older than specified days.
        
        Args:
            days: Number of days to keep
        """
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
        deleted_count = 0
        
        for bundle_file in self.base_path.rglob("*.tar.*"):
            if bundle_file.stat().st_mtime < cutoff_time:
                bundle_file.unlink()
                deleted_count += 1
        
        logger.info(f"Cleaned up {deleted_count} old bundles")

