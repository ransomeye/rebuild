# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant/metrics/exporter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Prometheus metrics exporter for SOC Copilot

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
    Prometheus metrics exporter for SOC Copilot.
    """
    
    def __init__(self):
        """Initialize metrics exporter."""
        if not PROMETHEUS_AVAILABLE:
            self.enabled = False
            return
        
        self.enabled = True
        
        # Metrics
        self.rag_query_latency = Histogram(
            'ransomeye_assistant_rag_query_latency_seconds',
            'Time spent processing RAG queries',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
        )
        
        self.docs_ingested_count = Counter(
            'ransomeye_assistant_docs_ingested_total',
            'Total number of documents ingested'
        )
        
        self.queries_total = Counter(
            'ransomeye_assistant_queries_total',
            'Total number of queries processed'
        )
        
        self.feedback_submitted = Counter(
            'ransomeye_assistant_feedback_submitted_total',
            'Total number of feedback submissions',
            ['rating']  # thumbs_up, thumbs_down, correction
        )
        
        self.vector_store_size = Gauge(
            'ransomeye_assistant_vector_store_size',
            'Number of vectors in the store'
        )
        
        logger.info("Metrics exporter initialized")
    
    def record_query_latency(self, duration: float):
        """
        Record RAG query latency.
        
        Args:
            duration: Query duration in seconds
        """
        if not self.enabled:
            return
        self.rag_query_latency.observe(duration)
    
    def record_doc_ingested(self, count: int = 1):
        """
        Record document ingestion.
        
        Args:
            count: Number of documents ingested
        """
        if not self.enabled:
            return
        for _ in range(count):
            self.docs_ingested_count.inc()
    
    def record_query(self):
        """Record a query."""
        if not self.enabled:
            return
        self.queries_total.inc()
    
    def record_feedback(self, rating: str):
        """
        Record feedback submission.
        
        Args:
            rating: Feedback rating (thumbs_up, thumbs_down, correction)
        """
        if not self.enabled:
            return
        self.feedback_submitted.labels(rating=rating).inc()
    
    def set_vector_store_size(self, size: int):
        """
        Set vector store size.
        
        Args:
            size: Number of vectors in store
        """
        if not self.enabled:
            return
        self.vector_store_size.set(size)
    
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

