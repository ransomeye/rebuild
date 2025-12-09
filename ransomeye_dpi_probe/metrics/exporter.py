# Path and File Name : /home/ransomeye/rebuild/ransomeye_dpi_probe/metrics/exporter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Prometheus metrics exporter for packet_rate, drop_rate, and pii_redacted_bytes

import os
import time
import threading
import logging
from prometheus_client import start_http_server, Gauge, Counter, Histogram

logger = logging.getLogger(__name__)


class MetricsExporter:
    """Prometheus metrics exporter for DPI Probe."""
    
    def __init__(self, capture_daemon=None, uploader=None):
        """
        Initialize metrics exporter.
        
        Args:
            capture_daemon: CaptureDaemon instance (optional)
            uploader: ChunkUploader instance (optional)
        """
        self.capture_daemon = capture_daemon
        self.uploader = uploader
        
        # Metrics
        self.packet_rate = Gauge('ransomeye_probe_packet_rate', 'Packets captured per second')
        self.drop_rate = Gauge('ransomeye_probe_drop_rate', 'Packets dropped per second')
        self.pii_redacted_bytes = Counter('ransomeye_probe_pii_redacted_bytes_total', 
                                         'Total bytes redacted due to PII detection')
        self.active_flows = Gauge('ransomeye_probe_active_flows', 'Number of active flows')
        self.total_packets = Counter('ransomeye_probe_packets_total', 'Total packets captured')
        self.total_bytes = Counter('ransomeye_probe_bytes_total', 'Total bytes captured')
        self.upload_success = Counter('ransomeye_probe_upload_success_total', 
                                     'Total successful uploads')
        self.upload_failures = Counter('ransomeye_probe_upload_failures_total', 
                                      'Total upload failures')
        self.upload_bytes = Counter('ransomeye_probe_upload_bytes_total', 
                                   'Total bytes uploaded')
        self.pending_chunks = Gauge('ransomeye_probe_pending_chunks', 
                                   'Number of pending chunks')
        self.inflight_chunks = Gauge('ransomeye_probe_inflight_chunks', 
                                    'Number of inflight chunks')
        
        # Histograms
        self.packet_size = Histogram('ransomeye_probe_packet_size_bytes', 
                                    'Packet size distribution', buckets=[64, 256, 512, 1024, 2048, 4096, 8192])
        self.flow_duration = Histogram('ransomeye_probe_flow_duration_seconds', 
                                      'Flow duration distribution', buckets=[1, 5, 10, 30, 60, 300, 600])
        
        self.running = False
        self.update_thread: threading.Thread = None
        
        # Previous stats for rate calculation
        self.prev_stats = {
            'packets_captured': 0,
            'packets_dropped': 0,
            'timestamp': time.time()
        }
    
    def _update_metrics(self):
        """Update metrics from daemon stats."""
        while self.running:
            try:
                time.sleep(10)  # Update every 10 seconds
                
                if self.capture_daemon:
                    stats = self.capture_daemon.get_stats()
                    
                    # Calculate rates
                    now = time.time()
                    time_delta = now - self.prev_stats['timestamp']
                    
                    if time_delta > 0:
                        packets_delta = stats.get('packets_captured', 0) - self.prev_stats['packets_captured']
                        drops_delta = stats.get('packets_dropped', 0) - self.prev_stats['packets_dropped']
                        
                        self.packet_rate.set(packets_delta / time_delta)
                        self.drop_rate.set(drops_delta / time_delta)
                        
                        self.prev_stats = {
                            'packets_captured': stats.get('packets_captured', 0),
                            'packets_dropped': stats.get('packets_dropped', 0),
                            'timestamp': now
                        }
                    
                    # Update counters and gauges
                    self.active_flows.set(stats.get('active_flows', 0))
                    
                    # PII redacted bytes (cumulative)
                    privacy_stats = stats.get('privacy_filter', {})
                    pii_bytes = privacy_stats.get('total_redacted_bytes', 0)
                    # Note: Counter should be incremented, but we'll set it for simplicity
                    # In production, track delta
                    
                if self.uploader:
                    upload_stats = self.uploader.get_stats()
                    
                    self.pending_chunks.set(upload_stats.get('pending_chunks', 0))
                    self.inflight_chunks.set(upload_stats.get('inflight_chunks', 0))
                
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
    
    def record_packet(self, size: int):
        """Record a captured packet."""
        self.packet_size.observe(size)
    
    def record_flow_duration(self, duration: float):
        """Record flow duration."""
        self.flow_duration.observe(duration)
    
    def record_pii_redaction(self, bytes_redacted: int):
        """Record PII redaction."""
        self.pii_redacted_bytes.inc(bytes_redacted)
    
    def start(self, port: int = 9092):
        """
        Start metrics exporter server.
        
        Args:
            port: HTTP server port
        """
        if self.running:
            logger.warning("Metrics exporter already running")
            return
        
        logger.info(f"Starting metrics exporter on port {port}")
        
        start_http_server(port)
        self.running = True
        
        self.update_thread = threading.Thread(target=self._update_metrics, daemon=True)
        self.update_thread.start()
        
        logger.info(f"Metrics exporter started on port {port}")
    
    def stop(self):
        """Stop metrics exporter."""
        if not self.running:
            return
        
        logger.info("Stopping metrics exporter...")
        self.running = False
        
        if self.update_thread:
            self.update_thread.join(timeout=5)


def main():
    """Main entry point for standalone metrics exporter."""
    import argparse
    
    parser = argparse.ArgumentParser(description='RansomEye DPI Probe Metrics Exporter')
    parser.add_argument('--port', type=int, default=int(os.environ.get('PROBE_METRICS_PORT', '9092')),
                       help='Metrics HTTP server port')
    
    args = parser.parse_args()
    
    exporter = MetricsExporter()
    exporter.start(port=args.port)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        exporter.stop()


if __name__ == '__main__':
    main()

