# Path and File Name : /home/ransomeye/rebuild/ransomeye_windows_agent/engine/persistence.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Atomic file writes to buffer directory using tempfile and os.replace (Windows-safe)

import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PersistenceManager:
    """Manages atomic writes to buffer directory (Windows-safe)."""
    
    def __init__(self):
        """Initialize persistence manager."""
        # Use ProgramData on Windows
        default_buffer = os.path.join(
            os.environ.get('PROGRAMDATA', 'C:\\ProgramData'),
            'RansomEye',
            'buffer'
        )
        
        self.buffer_dir = Path(os.environ.get('BUFFER_DIR', default_buffer))
        
        # Create buffer directories
        self.pending_dir = self.buffer_dir / 'pending'
        self.archive_dir = self.buffer_dir / 'archive'
        
        self.pending_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Buffer size limit
        self.max_buffer_mb = int(os.environ.get('AGENT_MAX_BUFFER_MB', '1000'))
        
        logger.info(f"Persistence manager initialized: {self.buffer_dir}")
    
    def save_event(self, event: Dict[str, Any]):
        """
        Save event to buffer using atomic write (Windows-safe).
        
        Args:
            event: Event dictionary to save
        """
        try:
            # Check buffer size
            if self._check_buffer_size():
                logger.warning("Buffer size limit reached, dropping event")
                return
            
            # Generate filename with timestamp
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
            filename = f"{timestamp}.json"
            final_path = self.pending_dir / filename
            
            # Atomic write: write to temp file first, then replace
            # Use os.replace which is atomic on Windows (Python 3.3+)
            with tempfile.NamedTemporaryFile(
                mode='w',
                dir=self.pending_dir,
                delete=False,
                suffix='.tmp',
                encoding='utf-8'
            ) as tmp_file:
                json.dump(event, tmp_file, indent=2, ensure_ascii=False)
                tmp_path = Path(tmp_file.name)
            
            # Atomic replace (Windows-safe)
            try:
                os.replace(str(tmp_path), str(final_path))
            except OSError as e:
                # If replace fails, try copy + delete
                logger.warning(f"os.replace failed: {e}, using copy+delete fallback")
                shutil.copy2(str(tmp_path), str(final_path))
                tmp_path.unlink()
            
            logger.debug(f"Event saved: {final_path}")
        
        except Exception as e:
            logger.error(f"Error saving event: {e}", exc_info=True)
    
    def get_pending_events(self, limit: int = 100) -> List[Path]:
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
                # Use replace for atomic move
                try:
                    os.replace(str(file_path), str(archive_path))
                except OSError:
                    # Fallback to copy + delete
                    shutil.copy2(str(file_path), str(archive_path))
                    file_path.unlink()
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
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading event: {e}")
            return {}
    
    def _check_buffer_size(self) -> bool:
        """
        Check if buffer size exceeds limit.
        
        Returns:
            True if buffer is too large
        """
        try:
            total_size = 0
            for file_path in self.pending_dir.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            
            # Convert to MB
            size_mb = total_size / (1024 * 1024)
            
            if size_mb > self.max_buffer_mb:
                logger.warning(f"Buffer size {size_mb:.2f} MB exceeds limit {self.max_buffer_mb} MB")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error checking buffer size: {e}")
            return False
    
    def cleanup_old_archives(self, days: int = 30):
        """
        Clean up archived events older than specified days.
        
        Args:
            days: Number of days to keep archives
        """
        try:
            cutoff_time = datetime.utcnow().timestamp() - (days * 24 * 60 * 60)
            
            for file_path in self.archive_dir.glob('*.json'):
                try:
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        logger.debug(f"Deleted old archive: {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting archive {file_path}: {e}")
        
        except Exception as e:
            logger.error(f"Error cleaning up archives: {e}")

