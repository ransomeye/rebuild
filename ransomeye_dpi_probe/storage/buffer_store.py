# Path and File Name : /home/ransomeye/rebuild/ransomeye_dpi_probe/storage/buffer_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Manages Pending/Inflight/Archived chunk storage

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BufferStore:
    """Manages buffer storage for chunks."""
    
    def __init__(self, buffer_dir: str):
        """
        Initialize buffer store.
        
        Args:
            buffer_dir: Root buffer directory
        """
        self.buffer_dir = Path(buffer_dir)
        self.pending_dir = self.buffer_dir / 'pending'
        self.inflight_dir = self.buffer_dir / 'inflight'
        self.archived_dir = self.buffer_dir / 'archived'
        
        for d in [self.pending_dir, self.inflight_dir, self.archived_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        self.max_pending_size_mb = int(os.environ.get('PROBE_MAX_PENDING_SIZE_MB', '5000'))
        self.max_archived_age_days = int(os.environ.get('PROBE_MAX_ARCHIVED_AGE_DAYS', '30'))
    
    def list_pending(self) -> List[Path]:
        """List all pending chunks."""
        return [f for f in self.pending_dir.iterdir() if f.is_file()]
    
    def list_inflight(self) -> List[Path]:
        """List all inflight chunks."""
        return [f for f in self.inflight_dir.iterdir() if f.is_file()]
    
    def list_archived(self) -> List[Path]:
        """List all archived chunks."""
        return [f for f in self.archived_dir.iterdir() if f.is_file()]
    
    def get_pending_size_mb(self) -> float:
        """Get total size of pending chunks in MB."""
        total = sum(f.stat().st_size for f in self.list_pending())
        return total / 1024 / 1024
    
    def get_inflight_size_mb(self) -> float:
        """Get total size of inflight chunks in MB."""
        total = sum(f.stat().st_size for f in self.list_inflight())
        return total / 1024 / 1024
    
    def get_archived_size_mb(self) -> float:
        """Get total size of archived chunks in MB."""
        total = sum(f.stat().st_size for f in self.list_archived())
        return total / 1024 / 1024
    
    def get_total_size_mb(self) -> float:
        """Get total buffer size in MB."""
        return (self.get_pending_size_mb() + 
                self.get_inflight_size_mb() + 
                self.get_archived_size_mb())
    
    def cleanup_old_archived(self):
        """Remove archived chunks older than max age."""
        from datetime import timedelta
        
        cutoff = datetime.now().timestamp() - (self.max_archived_age_days * 24 * 60 * 60)
        
        removed = 0
        for chunk in self.list_archived():
            if chunk.stat().st_mtime < cutoff:
                try:
                    chunk.unlink()
                    removed += 1
                except Exception as e:
                    logger.error(f"Error removing old archived chunk {chunk}: {e}")
        
        if removed > 0:
            logger.info(f"Removed {removed} old archived chunks")
        
        return removed
    
    def get_stats(self) -> Dict[str, Any]:
        """Get buffer statistics."""
        return {
            'pending_count': len(self.list_pending()),
            'pending_size_mb': self.get_pending_size_mb(),
            'inflight_count': len(self.list_inflight()),
            'inflight_size_mb': self.get_inflight_size_mb(),
            'archived_count': len(self.list_archived()),
            'archived_size_mb': self.get_archived_size_mb(),
            'total_size_mb': self.get_total_size_mb(),
            'max_pending_size_mb': self.max_pending_size_mb,
            'max_archived_age_days': self.max_archived_age_days
        }

