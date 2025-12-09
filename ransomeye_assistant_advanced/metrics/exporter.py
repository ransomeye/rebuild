# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant_advanced/metrics/exporter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Prometheus metrics exporter for ingest_count, OCR latency, playbook suggestion confidence

import os
import time
from typing import Optional
import logging

try:
    from prometheus_client import Counter, Histogram, Gauge, make_asgi_app
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("prometheus-client not available - metrics disabled")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Metrics
if PROMETHEUS_AVAILABLE:
    ingest_count = Counter(
        'assistant_advanced_ingest_total',
        'Total number of artifacts ingested',
        ['mime_type']
    )
    
    ocr_latency = Histogram(
        'assistant_advanced_ocr_duration_seconds',
        'OCR processing duration in seconds',
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
    )
    
    vision_latency = Histogram(
        'assistant_advanced_vision_duration_seconds',
        'Vision detection duration in seconds',
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
    )
    
    playbook_suggestion_confidence = Histogram(
        'assistant_advanced_playbook_confidence',
        'Playbook suggestion confidence score',
        buckets=[0.0, 0.25, 0.5, 0.75, 0.9, 0.95, 1.0]
    )
    
    playbook_suggestions_total = Counter(
        'assistant_advanced_playbook_suggestions_total',
        'Total number of playbook suggestions',
        ['playbook_id']
    )
    
    feedback_total = Counter(
        'assistant_advanced_feedback_total',
        'Total number of feedback submissions',
        ['accepted']
    )

def setup_metrics_endpoint(app):
    """
    Setup Prometheus metrics endpoint.
    
    Args:
        app: FastAPI application
    """
    if not PROMETHEUS_AVAILABLE:
        logger.warning("Prometheus not available - metrics endpoint not set up")
        return
    
    try:
        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)
        logger.info("Prometheus metrics endpoint mounted at /metrics")
    except Exception as e:
        logger.error(f"Error setting up metrics endpoint: {e}")

def record_ingest(mime_type: str):
    """Record artifact ingestion."""
    if PROMETHEUS_AVAILABLE:
        ingest_count.labels(mime_type=mime_type).inc()

def record_ocr_latency(duration: float):
    """Record OCR processing latency."""
    if PROMETHEUS_AVAILABLE:
        ocr_latency.observe(duration)

def record_vision_latency(duration: float):
    """Record vision detection latency."""
    if PROMETHEUS_AVAILABLE:
        vision_latency.observe(duration)

def record_playbook_suggestion(playbook_id: int, confidence: float):
    """Record playbook suggestion."""
    if PROMETHEUS_AVAILABLE:
        playbook_suggestion_confidence.observe(confidence)
        playbook_suggestions_total.labels(playbook_id=str(playbook_id)).inc()

def record_feedback(accepted: bool):
    """Record feedback submission."""
    if PROMETHEUS_AVAILABLE:
        feedback_total.labels(accepted=str(accepted).lower()).inc()

