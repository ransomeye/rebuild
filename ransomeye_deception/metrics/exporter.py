# Path and File Name : /home/ransomeye/rebuild/ransomeye_deception/metrics/exporter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Prometheus metrics exporter for active_decoys and decoy_hits_total

import os
from fastapi import FastAPI
from fastapi.responses import Response
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import prometheus_client
try:
    from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not available, metrics disabled")

class MetricsExporter:
    """
    Prometheus metrics exporter for Deception Framework.
    """
    
    def __init__(self):
        """Initialize metrics exporter."""
        if not PROMETHEUS_AVAILABLE:
            self.enabled = False
            return
        
        self.enabled = True
        
        # Metrics
        self.active_decoys = Gauge(
            'ransomeye_deception_active_decoys',
            'Number of active decoys',
            ['type']  # Label: file, service, process, host
        )
        
        self.decoy_hits_total = Counter(
            'ransomeye_deception_hits_total',
            'Total number of decoy interactions',
            ['type', 'event_type']  # Labels
        )
        
        self.rotations_total = Counter(
            'ransomeye_deception_rotations_total',
            'Total number of decoy rotations',
            ['type']
        )
        
        self.deployments_total = Counter(
            'ransomeye_deception_deployments_total',
            'Total number of decoy deployments',
            ['type']
        )
        
        logger.info("Metrics exporter initialized")
    
    def set_active_decoys(self, decoy_type: str, count: int):
        """
        Set active decoy count.
        
        Args:
            decoy_type: Type of decoy
            count: Number of active decoys
        """
        if not self.enabled:
            return
        self.active_decoys.labels(type=decoy_type).set(count)
    
    def record_hit(self, decoy_type: str, event_type: str):
        """
        Record decoy hit.
        
        Args:
            decoy_type: Type of decoy
            event_type: Type of event
        """
        if not self.enabled:
            return
        self.decoy_hits_total.labels(type=decoy_type, event_type=event_type).inc()
    
    def record_rotation(self, decoy_type: str):
        """Record decoy rotation."""
        if not self.enabled:
            return
        self.rotations_total.labels(type=decoy_type).inc()
    
    def record_deployment(self, decoy_type: str):
        """Record decoy deployment."""
        if not self.enabled:
            return
        self.deployments_total.labels(type=decoy_type).inc()
    
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
    
    logger.info("Metrics endpoint set up at /metrics")


def start_metrics_server(port: int = None):
    """
    Start Prometheus metrics HTTP server on separate port.
    
    Args:
        port: Port to listen on (defaults to DECEPTION_METRICS_PORT env var or 9096)
    """
    if not PROMETHEUS_AVAILABLE:
        logger.warning("Prometheus not available, cannot start metrics server")
        return
    
    metrics_port = port or int(os.environ.get('DECEPTION_METRICS_PORT', 9096))
    
    try:
        start_http_server(metrics_port)
        logger.info(f"Prometheus metrics server started on port {metrics_port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")
        raise

