# Path and File Name : /home/ransomeye/rebuild/ransomeye_linux_agent/transport/heartbeat.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Periodic heartbeat POST requests to Core API

import os
import time
import threading
from datetime import datetime
import logging

from .agent_client import AgentClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HeartbeatManager:
    """Manages periodic heartbeat to Core."""
    
    def __init__(self):
        """Initialize heartbeat manager."""
        self.client = AgentClient()
        self.interval = int(os.environ.get('HEARTBEAT_INTERVAL', '60'))  # seconds
        self.running = False
        self.thread = None
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
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Heartbeat stopped")
    
    def _heartbeat_loop(self):
        """Heartbeat loop."""
        while self.running:
            try:
                self._send_heartbeat()
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
            
            time.sleep(self.interval)
    
    def _send_heartbeat(self):
        """Send heartbeat to Core."""
        import socket
        import platform
        
        hostname = socket.gethostname()
        
        heartbeat_data = {
            "hostname": hostname,
            "timestamp": datetime.utcnow().isoformat(),
            "platform": platform.platform(),
            "agent_version": "1.0.0"
        }
        
        result = self.client.post('/api/agents/heartbeat', heartbeat_data)
        
        if result:
            logger.debug(f"Heartbeat sent successfully: {hostname}")
        else:
            logger.warning(f"Heartbeat failed: {hostname}")

