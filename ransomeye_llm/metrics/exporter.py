# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm/metrics/exporter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Prometheus metrics exporter for LLM summarizer

import os
import time
from typing import Dict, Any
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
    Prometheus metrics exporter for LLM summarizer.
    """
    
    def __init__(self):
        """Initialize metrics exporter."""
        if not PROMETHEUS_AVAILABLE:
            self.enabled = False
            return
        
        self.enabled = True
        
        # Metrics
        self.reports_generated_total = Counter(
            'ransomeye_llm_reports_generated_total',
            'Total number of reports generated',
            ['audience']  # Label: executive, manager, analyst
        )
        
        self.llm_inference_seconds = Histogram(
            'ransomeye_llm_inference_seconds',
            'Time spent on LLM inference',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        )
        
        self.llm_model_available = Gauge(
            'ransomeye_llm_model_available',
            'Whether LLM model is available (1) or not (0)'
        )
        
        self.reports_in_progress = Gauge(
            'ransomeye_llm_reports_in_progress',
            'Number of reports currently being generated'
        )
        
        logger.info("Metrics exporter initialized")
    
    def record_report_generated(self, audience: str):
        """
        Record that a report was generated.
        
        Args:
            audience: Target audience (executive, manager, analyst)
        """
        if not self.enabled:
            return
        self.reports_generated_total.labels(audience=audience).inc()
    
    def record_inference_time(self, duration: float):
        """
        Record LLM inference time.
        
        Args:
            duration: Inference duration in seconds
        """
        if not self.enabled:
            return
        self.llm_inference_seconds.observe(duration)
    
    def set_model_available(self, available: bool):
        """
        Set model availability status.
        
        Args:
            available: True if model is available, False otherwise
        """
        if not self.enabled:
            return
        self.llm_model_available.set(1 if available else 0)
    
    def set_reports_in_progress(self, count: int):
        """
        Set number of reports in progress.
        
        Args:
            count: Number of reports being generated
        """
        if not self.enabled:
            return
        self.reports_in_progress.set(count)
    
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

