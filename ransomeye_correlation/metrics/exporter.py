# Path and File Name : /home/ransomeye/rebuild/ransomeye_correlation/metrics/exporter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Prometheus metrics exporter for Threat Correlation Engine

import os
from fastapi import FastAPI
from fastapi.responses import Response
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import prometheus_client
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not available, metrics disabled")

class MetricsExporter:
    """
    Prometheus metrics exporter for Threat Correlation Engine.
    """
    
    def __init__(self):
        """Initialize metrics exporter."""
        if not PROMETHEUS_AVAILABLE:
            self.enabled = False
            return
        
        self.enabled = True
        
        # Metrics
        self.graph_nodes_total = Gauge(
            'ransomeye_correlation_graph_nodes_total',
            'Total number of nodes in the graph'
        )
        
        self.correlation_incidents_total = Counter(
            'ransomeye_correlation_incidents_total',
            'Total number of correlated incidents'
        )
        
        self.ingest_latency = Histogram(
            'ransomeye_correlation_ingest_latency_seconds',
            'Time spent processing alert ingestion',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        )
        
        logger.info("Metrics exporter initialized")
    
    def set_graph_nodes(self, count: int):
        """
        Set graph node count.
        
        Args:
            count: Number of nodes
        """
        if not self.enabled:
            return
        self.graph_nodes_total.set(count)
    
    def record_incident(self):
        """Record a correlated incident."""
        if not self.enabled:
            return
        self.correlation_incidents_total.inc()
    
    def record_ingest_latency(self, duration: float):
        """
        Record ingestion latency.
        
        Args:
            duration: Ingestion duration in seconds
        """
        if not self.enabled:
            return
        self.ingest_latency.observe(duration)
    
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

