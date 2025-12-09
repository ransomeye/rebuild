# Path and File Name : /home/ransomeye/rebuild/ransomeye_linux_agent/transport/uploader.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Worker thread that drains buffer, uploads events, and archives/deletes them

import os
from pathlib import Path
from typing import Optional
import logging

from .agent_client import AgentClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Uploader:
    """Uploads buffered events to Core."""
    
    def __init__(self, persistence):
        """
        Initialize uploader.
        
        Args:
            persistence: PersistenceManager instance
        """
        self.client = AgentClient()
        self.persistence = persistence
        self.batch_size = int(os.environ.get('UPLOAD_BATCH_SIZE', '10'))
        logger.info("Uploader initialized")
    
    def process_buffer(self):
        """Process pending events from buffer."""
        try:
            # Get pending events
            pending_files = self.persistence.get_pending_events(limit=self.batch_size)
            
            if not pending_files:
                return
            
            logger.info(f"Processing {len(pending_files)} pending events")
            
            # Upload each event
            for file_path in pending_files:
                success = self._upload_event(file_path)
                
                if success:
                    # Archive successful upload
                    self.persistence.archive_event(file_path)
                else:
                    # Keep file in pending for retry
                    logger.debug(f"Upload failed, keeping: {file_path}")
        
        except Exception as e:
            logger.error(f"Error processing buffer: {e}", exc_info=True)
    
    def _upload_event(self, file_path: Path) -> bool:
        """
        Upload single event to Core.
        
        Args:
            file_path: Path to event file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load event
            event = self.persistence.load_event(file_path)
            
            if not event:
                logger.warning(f"Empty event file: {file_path}")
                return False
            
            # Determine endpoint based on event type
            endpoint = '/api/agents/telemetry'
            if event.get('event_type') == 'threat_detected':
                endpoint = '/api/agents/alerts'
            
            # Upload to Core
            result = self.client.post(endpoint, event)
            
            if result:
                logger.debug(f"Event uploaded: {file_path.name}")
                return True
            else:
                logger.warning(f"Upload failed: {file_path.name}")
                return False
        
        except Exception as e:
            logger.error(f"Error uploading event {file_path}: {e}")
            return False

