# Path and File Name : /home/ransomeye/rebuild/ransomeye_windows_agent/engine/metrics_server.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: HTTP metrics server exposing Prometheus-compatible metrics on configurable port

import os
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for metrics endpoint."""
    
    metrics_data = {}
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; version=0.0.4')
            self.end_headers()
            
            # Generate Prometheus-compatible metrics
            metrics_text = self._generate_metrics()
            self.wfile.write(metrics_text.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.debug(f"{self.address_string()} - {format % args}")
    
    def _generate_metrics(self) -> str:
        """Generate Prometheus-compatible metrics text."""
        lines = []
        
        # Agent metrics
        lines.append("# HELP ransomeye_agent_info Agent information")
        lines.append("# TYPE ransomeye_agent_info gauge")
        lines.append('ransomeye_agent_info{version="1.0.0",platform="windows"} 1')
        
        # Buffer metrics
        buffer_size = self.metrics_data.get('buffer_size_bytes', 0)
        buffer_files = self.metrics_data.get('buffer_files_count', 0)
        
        lines.append("# HELP ransomeye_agent_buffer_size_bytes Buffer size in bytes")
        lines.append("# TYPE ransomeye_agent_buffer_size_bytes gauge")
        lines.append(f"ransomeye_agent_buffer_size_bytes {buffer_size}")
        
        lines.append("# HELP ransomeye_agent_buffer_files_count Number of files in buffer")
        lines.append("# TYPE ransomeye_agent_buffer_files_count gauge")
        lines.append(f"ransomeye_agent_buffer_files_count {buffer_files}")
        
        # Upload metrics
        uploads_total = self.metrics_data.get('uploads_total', 0)
        uploads_failed = self.metrics_data.get('uploads_failed', 0)
        
        lines.append("# HELP ransomeye_agent_uploads_total Total number of uploads")
        lines.append("# TYPE ransomeye_agent_uploads_total counter")
        lines.append(f"ransomeye_agent_uploads_total {uploads_total}")
        
        lines.append("# HELP ransomeye_agent_uploads_failed Total number of failed uploads")
        lines.append("# TYPE ransomeye_agent_uploads_failed counter")
        lines.append(f"ransomeye_agent_uploads_failed {uploads_failed}")
        
        # Detection metrics
        detections_total = self.metrics_data.get('detections_total', 0)
        
        lines.append("# HELP ransomeye_agent_detections_total Total number of threat detections")
        lines.append("# TYPE ransomeye_agent_detections_total counter")
        lines.append(f"ransomeye_agent_detections_total {detections_total}")
        
        # Heartbeat metrics
        last_heartbeat = self.metrics_data.get('last_heartbeat_timestamp', 0)
        
        lines.append("# HELP ransomeye_agent_last_heartbeat_timestamp Last heartbeat timestamp")
        lines.append("# TYPE ransomeye_agent_last_heartbeat_timestamp gauge")
        lines.append(f"ransomeye_agent_last_heartbeat_timestamp {last_heartbeat}")
        
        return '\n'.join(lines) + '\n'


class MetricsServer:
    """HTTP server for exposing metrics."""
    
    def __init__(self):
        """Initialize metrics server."""
        self.port = int(os.environ.get('AGENT_METRICS_PORT', '9111'))
        self.server = None
        self.server_thread = None
        self.running = False
        
        logger.info(f"Metrics server initialized (port: {self.port})")
    
    def start(self):
        """Start metrics server in background thread."""
        if self.running:
            return
        
        try:
            self.server = HTTPServer(('0.0.0.0', self.port), MetricsHandler)
            self.running = True
            
            self.server_thread = threading.Thread(
                target=self._serve,
                name="MetricsServerThread",
                daemon=True
            )
            self.server_thread.start()
            
            logger.info(f"Metrics server started on port {self.port}")
        
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
            self.running = False
    
    def stop(self):
        """Stop metrics server."""
        if not self.running:
            return
        
        self.running = False
        
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=2)
        
        logger.info("Metrics server stopped")
    
    def _serve(self):
        """Server main loop."""
        try:
            while self.running:
                self.server.handle_request()
        except Exception as e:
            logger.error(f"Metrics server error: {e}")
    
    def update_metrics(self, metrics: Dict[str, Any]):
        """Update metrics data."""
        MetricsHandler.metrics_data.update(metrics)

