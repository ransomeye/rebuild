# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/metrics/exporter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Prometheus metrics: ti_ingest_total, ti_dedupe_ratio

import os
from prometheus_client import Counter, Gauge, Histogram, start_http_server
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
ti_ingest_total = Counter(
    'ransomeye_ti_ingest_total',
    'Total number of IOCs ingested',
    ['source', 'type']
)

ti_dedupe_ratio = Gauge(
    'ransomeye_ti_dedupe_ratio',
    'Deduplication ratio (duplicates / total)',
    ['source']
)

ti_trust_score = Histogram(
    'ransomeye_ti_trust_score',
    'Trust score distribution',
    buckets=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
)

ti_campaigns_total = Gauge(
    'ransomeye_ti_campaigns_total',
    'Total number of campaigns'
)


def record_ingest(source: str, ioc_type: str):
    """Record IOC ingestion."""
    ti_ingest_total.labels(source=source, type=ioc_type).inc()


def update_dedupe_ratio(source: str, ratio: float):
    """Update deduplication ratio."""
    ti_dedupe_ratio.labels(source=source).set(ratio)


def record_trust_score(score: float):
    """Record trust score."""
    ti_trust_score.observe(score)


def update_campaigns_count(count: int):
    """Update campaigns count."""
    ti_campaigns_total.set(count)


def setup_metrics_endpoint(port: int = None):
    """Setup Prometheus metrics server."""
    metrics_port = port or int(os.environ.get('TI_METRICS_PORT', 9095))
    
    try:
        start_http_server(metrics_port)
        logger.info(f"Metrics server started on port {metrics_port}")
    except Exception as e:
        logger.error(f"Error starting metrics server: {e}")


if __name__ == '__main__':
    setup_metrics_endpoint()

