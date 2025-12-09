# Path and File Name : /home/ransomeye/rebuild/ransomeye_windows_agent/transport/heartbeat.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Periodic heartbeat to Core API reporting agent status and health

import os
import time
import threading
import socket
from typing import Optional
import logging

from .agent_client import AgentClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HeartbeatManager:
    """Manages periodic heartbeat to Core API."""
    
    def __init__(self):
        """Initialize heartbeat manager."""
        self.client = AgentClient()
        self.running = False
        self.thread = None
        self.interval = int(os.environ.get('HEARTBEAT_INTERVAL_SEC', '60'))
        self.hostname = os.environ.get('COMPUTERNAME', socket.gethostname())
        
        logger.info(f"Heartbeat manager initialized (interval: {self.interval}s)")
    
    def start(self):
        """Start heartbeat thread."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.thread.start()
        logger.info("Heartbeat started")
    
    def stop(self):
        """Stop heartbeat thread."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        logger.info("Heartbeat stopped")
    
    def _heartbeat_loop(self):
        """Main heartbeat loop."""
        while self.running:
            try:
                self.send_heartbeat()
            except Exception as e:
                logger.error(f"Heartbeat error: {e}", exc_info=True)
            
            # Sleep for interval
            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)
    
    def send_heartbeat(self) -> bool:
        """
        Send heartbeat to Core API.
        
        Returns:
            True if successful
        """
        try:
            heartbeat_data = {
                "hostname": self.hostname,
                "platform": "windows",
                "timestamp": time.time(),
                "status": "healthy"
            }
            
            response = self.client.post('/api/v1/agent/heartbeat', heartbeat_data)
            
            if response:
                logger.debug(f"Heartbeat sent: {self.hostname}")
                return True
            else:
                logger.warning(f"Heartbeat failed: {self.hostname}")
                return False
        
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            return False
    
    def send_heartbeat_now(self) -> bool:
        """
        Send heartbeat immediately (synchronous).
        
        Returns:
            True if successful
        """
        return self.send_heartbeat()

