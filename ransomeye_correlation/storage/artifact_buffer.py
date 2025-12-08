# Path and File Name : /home/ransomeye/rebuild/ransomeye_correlation/storage/artifact_buffer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Buffers incoming events before graph processing

from collections import deque
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArtifactBuffer:
    """
    Buffers incoming alerts before graph processing.
    """
    
    def __init__(self, max_size: int = 10000):
        """
        Initialize artifact buffer.
        
        Args:
            max_size: Maximum buffer size
        """
        self.buffer = deque(maxlen=max_size)
        self.max_size = max_size
    
    def add_alerts(self, alerts: List[Dict[str, Any]]):
        """
        Add alerts to buffer.
        
        Args:
            alerts: List of alert dictionaries
        """
        for alert in alerts:
            if len(self.buffer) >= self.max_size:
                logger.warning("Buffer full, dropping oldest alert")
            self.buffer.append(alert)
        
        logger.debug(f"Added {len(alerts)} alerts to buffer (total: {len(self.buffer)})")
    
    def get_alerts(self, count: int = None) -> List[Dict[str, Any]]:
        """
        Get alerts from buffer.
        
        Args:
            count: Number of alerts to retrieve (None for all)
            
        Returns:
            List of alert dictionaries
        """
        if count is None:
            alerts = list(self.buffer)
            self.buffer.clear()
        else:
            alerts = [self.buffer.popleft() for _ in range(min(count, len(self.buffer)))]
        
        return alerts
    
    def size(self) -> int:
        """Get current buffer size."""
        return len(self.buffer)

