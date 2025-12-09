# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/metrics/exporter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Prometheus metrics exporter

import os
from fastapi import FastAPI
from typing import Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import prometheus client
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    from fastapi.responses import Response
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not available. Install: pip install prometheus-client")


# Metrics
if PROMETHEUS_AVAILABLE:
    requests_total = Counter('llm_behavior_requests_total', 'Total requests')
    request_duration = Histogram('llm_behavior_request_duration_seconds', 'Request duration')
    confidence_score = Histogram('llm_behavior_confidence_score', 'Confidence scores')
    cache_hits = Counter('llm_behavior_cache_hits_total', 'Cache hits')
    security_blocks = Counter('llm_behavior_security_blocks_total', 'Security blocks')


def setup_metrics_endpoint(app: FastAPI):
    """
    Setup Prometheus metrics endpoint.
    
    Args:
        app: FastAPI application
    """
    if not PROMETHEUS_AVAILABLE:
        logger.warning("Prometheus not available. Metrics endpoint not set up.")
        return
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
    
    logger.info("Metrics endpoint set up at /metrics")

