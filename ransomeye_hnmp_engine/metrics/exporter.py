# Path and File Name : /home/ransomeye/rebuild/ransomeye_hnmp_engine/metrics/exporter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Prometheus metrics exporter for compliance_percentage and fleet_health_avg

import os
from fastapi import FastAPI
from fastapi.responses import Response
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import prometheus_client
try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not available, metrics disabled")

class MetricsExporter:
    """
    Prometheus metrics exporter for HNMP Engine.
    """
    
    def __init__(self):
        """Initialize metrics exporter."""
        if not PROMETHEUS_AVAILABLE:
            self.enabled = False
            return
        
        self.enabled = True
        
        # Metrics
        self.compliance_percentage = Gauge(
            'ransomeye_hnmp_compliance_percentage',
            'Percentage of hosts passing compliance checks',
            ['severity']  # Label: critical, high, medium, low
        )
        
        self.fleet_health_avg = Gauge(
            'ransomeye_hnmp_fleet_health_avg',
            'Average health score across all hosts'
        )
        
        self.hosts_total = Gauge(
            'ransomeye_hnmp_hosts_total',
            'Total number of hosts in inventory'
        )
        
        self.compliance_checks_total = Counter(
            'ransomeye_hnmp_compliance_checks_total',
            'Total number of compliance checks performed',
            ['severity', 'passed']  # Labels
        )
        
        self.score_calculations_total = Counter(
            'ransomeye_hnmp_score_calculations_total',
            'Total number of health scores calculated'
        )
        
        logger.info("Metrics exporter initialized")
    
    def set_compliance_percentage(self, severity: str, percentage: float):
        """
        Set compliance percentage for severity level.
        
        Args:
            severity: Severity level (critical, high, medium, low)
            percentage: Percentage value (0.0 - 100.0)
        """
        if not self.enabled:
            return
        self.compliance_percentage.labels(severity=severity).set(percentage)
    
    def set_fleet_health_avg(self, avg_score: float):
        """
        Set average fleet health score.
        
        Args:
            avg_score: Average health score (0.0 - 100.0)
        """
        if not self.enabled:
            return
        self.fleet_health_avg.set(avg_score)
    
    def set_hosts_total(self, count: int):
        """
        Set total hosts count.
        
        Args:
            count: Number of hosts
        """
        if not self.enabled:
            return
        self.hosts_total.set(count)
    
    def record_compliance_check(self, severity: str, passed: bool):
        """Record a compliance check."""
        if not self.enabled:
            return
        self.compliance_checks_total.labels(severity=severity, passed=str(passed).lower()).inc()
    
    def record_score_calculation(self):
        """Record a health score calculation."""
        if not self.enabled:
            return
        self.score_calculations_total.inc()
    
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

