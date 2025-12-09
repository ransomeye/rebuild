# Path and File Name : /home/ransomeye/rebuild/ransomeye_orchestrator/storage/temp_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Staging area for in-progress bundle builds

import os
import logging
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TempStore:
    """Staging area for in-progress builds."""
    
    def __init__(self, base_path: str = None):
        """
        Initialize temp store.
        
        Args:
            base_path: Base path for temp storage (default: OUTPUT_DIR/temp)
        """
        if base_path is None:
            base_path = os.environ.get('OUTPUT_DIR', '/home/ransomeye/rebuild/data')
            base_path = os.path.join(base_path, 'temp')
        
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def create_temp_dir(self, prefix: str = "bundle_") -> Path:
        """
        Create temporary directory for bundle build.
        
        Args:
            prefix: Directory name prefix
        
        Returns:
            Path to temporary directory
        """
        temp_dir = self.base_path / f"{prefix}{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir
    
    def cleanup_old_temp(self, hours: int = 24):
        """
        Clean up temporary directories older than specified hours.
        
        Args:
            hours: Number of hours to keep
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        deleted_count = 0
        
        for temp_dir in self.base_path.iterdir():
            if not temp_dir.is_dir():
                continue
            
            # Check modification time
            mtime = datetime.fromtimestamp(temp_dir.stat().st_mtime)
            if mtime < cutoff_time:
                import shutil
                shutil.rmtree(temp_dir)
                deleted_count += 1
        
        logger.info(f"Cleaned up {deleted_count} old temporary directories")

