# Path and File Name : /home/ransomeye/rebuild/ransomeye_alert_engine/metrics/exporter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Prometheus metrics exporter on port 9091 for alerts_processed, alerts_deduped, policy_reload_count

import os
from prometheus_client import start_http_server, Counter, Gauge
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define metrics
alerts_processed = Counter(
    'ransomeye_alerts_processed_total',
    'Total number of alerts processed',
    ['status']
)

alerts_deduped = Counter(
    'ransomeye_alerts_deduped_total',
    'Total number of alerts deduplicated',
    ['duplicate_type']
)

policy_reload_count = Counter(
    'ransomeye_policy_reloads_total',
    'Total number of policy reloads'
)

active_rules = Gauge(
    'ransomeye_active_rules',
    'Number of active policy rules'
)

def start_metrics_server(port: int = None):
    """
    Start Prometheus metrics HTTP server.
    
    Args:
        port: Port to listen on (defaults to EXPORTER_METRICS_PORT env var or 9091)
    """
    metrics_port = port or int(os.environ.get('EXPORTER_METRICS_PORT', 9091))
    
    try:
        start_http_server(metrics_port)
        logger.info(f"Prometheus metrics server started on port {metrics_port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")
        raise

def record_alert_processed(status: str = 'processed'):
    """
    Record that an alert was processed.
    
    Args:
        status: Status of processing (processed, duplicate, error)
    """
    alerts_processed.labels(status=status).inc()

def record_alert_deduped(duplicate_type: str):
    """
    Record that an alert was deduplicated.
    
    Args:
        duplicate_type: Type of duplicate (exact, fuzzy)
    """
    alerts_deduped.labels(duplicate_type=duplicate_type).inc()

def record_policy_reload():
    """Record that a policy was reloaded."""
    policy_reload_count.inc()

def set_active_rules_count(count: int):
    """
    Set the number of active rules.
    
    Args:
        count: Number of active rules
    """
    active_rules.set(count)

if __name__ == "__main__":
    start_metrics_server()

