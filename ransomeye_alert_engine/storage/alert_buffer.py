# Path and File Name : /home/ransomeye/rebuild/ransomeye_alert_engine/storage/alert_buffer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: High-throughput write buffer for async alert storage to prevent API blocking

import os
import json
import threading
import queue
import time
from pathlib import Path
from typing import Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertBuffer:
    """
    High-throughput write buffer for alerts.
    Writes to disk/DB asynchronously to prevent API blocking.
    """
    
    def __init__(self, buffer_size: int = 1000, flush_interval: float = 5.0,
                 storage_path: str = None):
        """
        Initialize alert buffer.
        
        Args:
            buffer_size: Maximum buffer size before forced flush
            flush_interval: Time in seconds between automatic flushes
            storage_path: Path to store alerts
        """
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.storage_path = Path(storage_path or os.environ.get(
            'ALERT_STORAGE_PATH',
            '/home/ransomeye/rebuild/ransomeye_alert_engine/storage/alerts'
        ))
        
        # Create storage directory
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Thread-safe queue for alerts
        self.alert_queue = queue.Queue(maxsize=buffer_size * 2)
        
        # Background writer thread
        self.running = False
        self.writer_thread = None
        self._start_writer()
    
    def _start_writer(self):
        """Start background writer thread."""
        self.running = True
        self.writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self.writer_thread.start()
        logger.info("Alert buffer writer thread started")
    
    def buffer_alert(self, alert_data: Dict[str, Any]):
        """
        Add alert to buffer (non-blocking).
        
        Args:
            alert_data: Alert data dictionary
        """
        try:
            self.alert_queue.put_nowait(alert_data)
        except queue.Full:
            logger.warning("Alert buffer full, dropping alert")
            # In production, might want to write to emergency file
    
    def _writer_loop(self):
        """Background thread loop for writing alerts."""
        alerts_batch = []
        last_flush = time.time()
        
        while self.running:
            try:
                # Get alert from queue (with timeout)
                try:
                    alert = self.alert_queue.get(timeout=1.0)
                    alerts_batch.append(alert)
                except queue.Empty:
                    pass
                
                # Flush if batch is full or interval has passed
                current_time = time.time()
                should_flush = (
                    len(alerts_batch) >= self.buffer_size or
                    (alerts_batch and current_time - last_flush >= self.flush_interval)
                )
                
                if should_flush:
                    self._flush_batch(alerts_batch)
                    alerts_batch = []
                    last_flush = current_time
                    
            except Exception as e:
                logger.error(f"Error in alert writer loop: {e}")
    
    def _flush_batch(self, alerts: list):
        """
        Flush batch of alerts to storage.
        
        Args:
            alerts: List of alert dictionaries
        """
        if not alerts:
            return
        
        try:
            # Write to file (in production, might write to database)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            batch_file = self.storage_path / f"alerts_{timestamp}.jsonl"
            
            with open(batch_file, 'a') as f:
                for alert in alerts:
                    f.write(json.dumps(alert) + '\n')
            
            logger.debug(f"Flushed {len(alerts)} alerts to {batch_file}")
            
        except Exception as e:
            logger.error(f"Error flushing alert batch: {e}")
    
    def flush(self):
        """Manually flush all buffered alerts."""
        alerts = []
        while not self.alert_queue.empty():
            try:
                alerts.append(self.alert_queue.get_nowait())
            except queue.Empty:
                break
        
        if alerts:
            self._flush_batch(alerts)
    
    def stop(self):
        """Stop the buffer and flush remaining alerts."""
        self.running = False
        if self.writer_thread:
            self.writer_thread.join(timeout=10)
        self.flush()

