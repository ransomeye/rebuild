# Path and File Name : /home/ransomeye/rebuild/ransomeye_linux_agent/engine/persistence.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Atomic file writes to buffer directory using tempfile and os.rename

import os
import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PersistenceManager:
    """Manages atomic writes to buffer directory."""
    
    def __init__(self):
        """Initialize persistence manager."""
        self.buffer_dir = Path(os.environ.get(
            'BUFFER_DIR',
            '/var/lib/ransomeye-agent/buffer'
        ))
        
        # Create buffer directories
        self.pending_dir = self.buffer_dir / 'pending'
        self.archive_dir = self.buffer_dir / 'archive'
        
        self.pending_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Persistence manager initialized: {self.buffer_dir}")
    
    def save_event(self, event: Dict[str, Any]):
        """
        Save event to buffer using atomic write.
        
        Args:
            event: Event dictionary to save
        """
        try:
            # Generate filename with timestamp
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
            filename = f"{timestamp}.json"
            final_path = self.pending_dir / filename
            
            # Atomic write: write to temp file first, then rename
            with tempfile.NamedTemporaryFile(
                mode='w',
                dir=self.pending_dir,
                delete=False,
                suffix='.tmp'
            ) as tmp_file:
                json.dump(event, tmp_file, indent=2)
                tmp_path = Path(tmp_file.name)
            
            # Atomic rename
            tmp_path.rename(final_path)
            
            logger.debug(f"Event saved: {final_path}")
        
        except Exception as e:
            logger.error(f"Error saving event: {e}", exc_info=True)
    
    def get_pending_events(self, limit: int = 100) -> list:
        """
        Get list of pending event files.
        
        Args:
            limit: Maximum number of files to return
            
        Returns:
            List of Path objects for pending event files
        """
        try:
            files = sorted(self.pending_dir.glob('*.json'))
            return files[:limit]
        except Exception as e:
            logger.error(f"Error getting pending events: {e}")
            return []
    
    def archive_event(self, file_path: Path):
        """
        Move event file to archive.
        
        Args:
            file_path: Path to event file
        """
        try:
            if file_path.exists():
                archive_path = self.archive_dir / file_path.name
                file_path.rename(archive_path)
                logger.debug(f"Event archived: {archive_path}")
        except Exception as e:
            logger.error(f"Error archiving event: {e}")
    
    def delete_event(self, file_path: Path):
        """
        Delete event file.
        
        Args:
            file_path: Path to event file
        """
        try:
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Event deleted: {file_path}")
        except Exception as e:
            logger.error(f"Error deleting event: {e}")
    
    def load_event(self, file_path: Path) -> Dict[str, Any]:
        """
        Load event from file.
        
        Args:
            file_path: Path to event file
            
        Returns:
            Event dictionary
        """
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading event: {e}")
            return {}

