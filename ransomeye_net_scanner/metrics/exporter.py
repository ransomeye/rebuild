# Path and File Name : /home/ransomeye/rebuild/ransomeye_net_scanner/metrics/exporter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Prometheus metrics exporter for Network Scanner

import os
from fastapi import FastAPI
from fastapi.responses import Response
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import prometheus_client
try:
    from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not available, metrics disabled")

class MetricsExporter:
    """
    Prometheus metrics exporter for Network Scanner.
    """
    
    def __init__(self):
        """Initialize metrics exporter."""
        if not PROMETHEUS_AVAILABLE:
            self.enabled = False
            return
        
        self.enabled = True
        
        # Metrics
        self.net_assets_total = Gauge(
            'ransomeye_net_scanner_assets_total',
            'Total number of network assets discovered'
        )
        
        self.net_vulnerabilities_total = Gauge(
            'ransomeye_net_scanner_vulnerabilities_total',
            'Total number of vulnerabilities detected'
        )
        
        self.active_scans_total = Counter(
            'ransomeye_net_scanner_active_scans_total',
            'Total number of active scans performed'
        )
        
        logger.info("Metrics exporter initialized")
    
    def set_assets_count(self, count: int):
        """
        Set asset count.
        
        Args:
            count: Number of assets
        """
        if not self.enabled:
            return
        self.net_assets_total.set(count)
    
    def set_vulnerabilities_count(self, count: int):
        """
        Set vulnerability count.
        
        Args:
            count: Number of vulnerabilities
        """
        if not self.enabled:
            return
        self.net_vulnerabilities_total.set(count)
    
    def record_active_scan(self):
        """Record an active scan."""
        if not self.enabled:
            return
        self.active_scans_total.inc()
    
    def get_metrics_response(self) -> Response:
        """
        Get Prometheus metrics response.
        
        Returns:
            FastAPI Response with metrics
        """
        if not self.enabled:
            return Response(
                content="# Metrics disabled (prometheus_client not available)\n",
                media_type="text/plain"
            )
        
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )

# Global metrics exporter instance
metrics_exporter = MetricsExporter()

def setup_metrics_endpoint(app: FastAPI):
    """
    Setup metrics endpoint on FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        return metrics_exporter.get_metrics_response()

