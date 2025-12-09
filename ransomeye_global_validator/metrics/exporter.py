# Path and File Name : /home/ransomeye/rebuild/ransomeye_global_validator/metrics/exporter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Prometheus metrics exporter for validator runs and success rates on port 9104

import os
import time
from prometheus_client import start_http_server, Counter, Gauge, Histogram
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
validator_runs_total = Counter(
    'validator_runs_total',
    'Total number of validation runs',
    ['scenario_type', 'status']
)

validator_success_rate = Gauge(
    'validator_success_rate',
    'Success rate of validation runs',
    ['scenario_type']
)

validator_run_duration = Histogram(
    'validator_run_duration_seconds',
    'Duration of validation runs in seconds',
    ['scenario_type'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]
)

validator_api_latency = Histogram(
    'validator_api_latency_seconds',
    'API latency during validation runs',
    ['api_name'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

validator_ml_health_score = Gauge(
    'validator_ml_health_score',
    'ML model health score for validation runs',
    ['run_id']
)


class MetricsExporter:
    """Prometheus metrics exporter for validator."""
    
    def __init__(self):
        """Initialize metrics exporter."""
        self.metrics_port = int(os.environ.get('VALIDATOR_METRICS_PORT', 9104))
        self.server_started = False
        logger.info("Metrics exporter initialized")
    
    def start_server(self):
        """Start Prometheus metrics server."""
        if not self.server_started:
            try:
                start_http_server(self.metrics_port)
                self.server_started = True
                logger.info(f"Metrics server started on port {self.metrics_port}")
            except Exception as e:
                logger.error(f"Failed to start metrics server: {e}")
    
    def record_run(self, scenario_type: str, status: str, duration: float):
        """
        Record validation run metrics.
        
        Args:
            scenario_type: Type of scenario
            status: Run status (passed/failed)
            duration: Run duration in seconds
        """
        validator_runs_total.labels(scenario_type=scenario_type, status=status).inc()
        validator_run_duration.labels(scenario_type=scenario_type).observe(duration)
    
    def record_api_latency(self, api_name: str, latency: float):
        """
        Record API latency.
        
        Args:
            api_name: Name of API
            latency: Latency in seconds
        """
        validator_api_latency.labels(api_name=api_name).observe(latency)
    
    def record_ml_health_score(self, run_id: str, score: float):
        """
        Record ML health score.
        
        Args:
            run_id: Run identifier
            score: Health score (0-1)
        """
        validator_ml_health_score.labels(run_id=run_id).set(score)
    
    def update_success_rate(self, scenario_type: str, rate: float):
        """
        Update success rate gauge.
        
        Args:
            scenario_type: Type of scenario
            rate: Success rate (0-1)
        """
        validator_success_rate.labels(scenario_type=scenario_type).set(rate)


def start_metrics_server():
    """Start metrics server (for use in main application)."""
    exporter = MetricsExporter()
    exporter.start_server()
    return exporter

