# Path and File Name : /home/ransomeye/rebuild/ransomeye_alert_engine/loader/policy_watchdog.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Background thread that polls for new policy bundles in a directory

import os
import threading
import time
from pathlib import Path
from typing import Optional
import logging

from .policy_loader import get_policy_loader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PolicyWatchdog:
    """
    Background thread that polls for new policy bundles
    in a specific directory and automatically loads them.
    """
    
    def __init__(self, watch_directory: str = None, poll_interval: int = 60):
        """
        Initialize watchdog.
        
        Args:
            watch_directory: Directory to watch for new bundles
            poll_interval: Polling interval in seconds
        """
        self.watch_directory = Path(watch_directory or os.environ.get(
            'POLICY_WATCH_DIR',
            '/home/ransomeye/rebuild/ransomeye_alert_engine/policies/watch'
        ))
        self.poll_interval = poll_interval
        self.running = False
        self.thread = None
        self.loaded_bundles = set()
        self.policy_loader = get_policy_loader()
        
        # Create watch directory if it doesn't exist
        self.watch_directory.mkdir(parents=True, exist_ok=True)
    
    def start(self):
        """Start the watchdog thread."""
        if self.running:
            logger.warning("Watchdog is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.thread.start()
        logger.info(f"Policy watchdog started, watching: {self.watch_directory}")
    
    def stop(self):
        """Stop the watchdog thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Policy watchdog stopped")
    
    def _watch_loop(self):
        """Main watchdog loop."""
        while self.running:
            try:
                self._check_for_new_bundles()
            except Exception as e:
                logger.error(f"Error in watchdog loop: {e}")
            
            # Sleep for poll interval
            time.sleep(self.poll_interval)
    
    def _check_for_new_bundles(self):
        """Check for new policy bundles and load them."""
        if not self.watch_directory.exists():
            return
        
        # Find all .tar.gz files
        bundle_files = list(self.watch_directory.glob("*.tar.gz"))
        
        for bundle_path in bundle_files:
            # Check if we've already loaded this bundle
            bundle_id = f"{bundle_path.name}_{bundle_path.stat().st_mtime}"
            
            if bundle_id in self.loaded_bundles:
                continue
            
            try:
                logger.info(f"Watchdog detected new bundle: {bundle_path}")
                
                # Load the bundle
                result = self.policy_loader.load_policy_bundle(bundle_path)
                
                # Mark as loaded
                self.loaded_bundles.add(bundle_id)
                
                logger.info(f"Watchdog loaded bundle: {bundle_path.name}, version: {result.get('version')}")
                
                # Optionally move or archive the bundle
                # archive_path = self.watch_directory / "loaded" / bundle_path.name
                # archive_path.parent.mkdir(exist_ok=True)
                # bundle_path.rename(archive_path)
                
            except Exception as e:
                logger.error(f"Watchdog failed to load bundle {bundle_path}: {e}")
                # Don't mark as loaded so we can retry

