# Path and File Name : /home/ransomeye/rebuild/ransomeye_net_scanner/engine/scheduler.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Background thread/cron to trigger active scans periodically

import os
import threading
import time
from typing import List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScanScheduler:
    """
    Schedules periodic active scans.
    """
    
    def __init__(self):
        """Initialize scan scheduler."""
        self.running = False
        self.scheduler_thread = None
        self.scan_interval = int(os.environ.get('SCAN_INTERVAL_SECONDS', 3600))  # Default 1 hour
        self.scan_subnets = os.environ.get('SCAN_SUBNETS', '').split(',')
        self.scan_subnets = [s.strip() for s in self.scan_subnets if s.strip()]
        self.scan_intensity = os.environ.get('SCAN_INTENSITY', 'T3')
    
    def start(self):
        """Start scheduler."""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        logger.info(f"Scheduler started (interval: {self.scan_interval}s)")
    
    def stop(self):
        """Stop scheduler."""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("Scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop."""
        from ..engine.active_scanner import ActiveScanner
        from ..engine.asset_manager import AssetManager
        
        active_scanner = ActiveScanner()
        asset_manager = AssetManager()
        
        while self.running:
            try:
                if self.scan_subnets:
                    logger.info(f"Running scheduled scan on {len(self.scan_subnets)} subnets")
                    
                    for subnet in self.scan_subnets:
                        try:
                            scan_result = active_scanner.scan_subnet(subnet, self.scan_intensity)
                            asset_manager.process_scan_results(scan_result)
                        except Exception as e:
                            logger.error(f"Error in scheduled scan for {subnet}: {e}")
                
                # Sleep until next scan
                time.sleep(self.scan_interval)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                time.sleep(60)  # Wait before retrying

