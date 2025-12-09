# Path and File Name : /home/ransomeye/rebuild/ransomeye_windows_agent/engine/agent_main.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Main entrypoint for Windows Agent with thread management and component orchestration

import os
import sys
import threading
import time
from pathlib import Path
from typing import Optional
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .collector_etw import ETWCollector
from .detector import Detector
from .persistence import PersistenceManager
from ..transport.heartbeat import HeartbeatManager
from ..transport.uploader import Uploader
from ..security.config_validator import ConfigValidator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgentMain:
    """Main agent process manager for Windows."""
    
    def __init__(self):
        """Initialize agent main process."""
        self.running = False
        self.collector = None
        self.detector = None
        self.persistence = None
        self.heartbeat = None
        self.uploader = None
        self.collector_thread = None
        self.uploader_thread = None
        
        # Validate configuration
        validator = ConfigValidator()
        if not validator.validate():
            logger.error("Configuration validation failed")
            sys.exit(1)
        
        logger.info("Windows Agent main process initialized")
    
    def setup_components(self):
        """Initialize all agent components."""
        try:
            # Initialize persistence first (needed by others)
            self.persistence = PersistenceManager()
            
            # Initialize detector
            self.detector = Detector()
            
            # Initialize ETW collector
            self.collector = ETWCollector(
                detector=self.detector,
                persistence=self.persistence
            )
            
            # Initialize transport components
            self.heartbeat = HeartbeatManager()
            self.uploader = Uploader(persistence=self.persistence)
            
            logger.info("All components initialized successfully")
        
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}", exc_info=True)
            sys.exit(1)
    
    def _start_threads(self):
        """Start all background threads."""
        # Start collector thread
        self.collector_thread = threading.Thread(
            target=self._collector_loop,
            name="CollectorThread",
            daemon=True
        )
        self.collector_thread.start()
        
        # Start uploader thread
        self.uploader_thread = threading.Thread(
            target=self._uploader_loop,
            name="UploaderThread",
            daemon=True
        )
        self.uploader_thread.start()
        
        # Start heartbeat in separate thread
        heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name="HeartbeatThread",
            daemon=True
        )
        heartbeat_thread.start()
        
        logger.info("All threads started")
    
    def start(self):
        """Start the agent (console mode)."""
        logger.info("Starting RansomEye Windows Agent...")
        
        self.setup_components()
        self.running = True
        
        # Start threads
        self._start_threads()
        
        logger.info("Agent started successfully")
        
        # Main loop
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            self.stop()
    
    def _collector_loop(self):
        """Collector thread main loop."""
        logger.info("Collector thread started")
        
        # Start ETW session
        if self.collector:
            try:
                self.collector.start_session()
            except Exception as e:
                logger.error(f"Failed to start ETW session: {e}")
        
        while self.running:
            try:
                if self.collector:
                    self.collector.collect_events()
                time.sleep(5)  # Process events every 5 seconds
            except Exception as e:
                logger.error(f"Collector error: {e}", exc_info=True)
                time.sleep(10)  # Wait longer on error
        
        # Stop ETW session
        if self.collector:
            try:
                self.collector.stop_session()
            except Exception as e:
                logger.error(f"Error stopping ETW session: {e}")
    
    def _uploader_loop(self):
        """Uploader thread main loop."""
        logger.info("Uploader thread started")
        
        while self.running:
            try:
                if self.uploader:
                    self.uploader.process_buffer()
                time.sleep(10)  # Check buffer every 10 seconds
            except Exception as e:
                logger.error(f"Uploader error: {e}", exc_info=True)
                time.sleep(30)  # Wait longer on error
    
    def _heartbeat_loop(self):
        """Heartbeat thread main loop."""
        logger.info("Heartbeat thread started")
        
        if self.heartbeat:
            self.heartbeat.start()
    
    def stop(self):
        """Stop the agent gracefully."""
        logger.info("Stopping agent...")
        self.running = False
        
        # Stop heartbeat
        if self.heartbeat:
            self.heartbeat.stop()
        
        # Stop collector
        if self.collector:
            try:
                self.collector.stop_session()
            except Exception as e:
                logger.error(f"Error stopping collector: {e}")
        
        # Wait for threads to finish
        if self.collector_thread and self.collector_thread.is_alive():
            self.collector_thread.join(timeout=5)
        
        if self.uploader_thread and self.uploader_thread.is_alive():
            self.uploader_thread.join(timeout=5)
        
        logger.info("Agent stopped")


def main():
    """Main entry point for console mode."""
    agent = AgentMain()
    agent.start()


if __name__ == "__main__":
    main()

