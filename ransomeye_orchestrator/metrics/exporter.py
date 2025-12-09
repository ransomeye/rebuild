# Path and File Name : /home/ransomeye/rebuild/ransomeye_orchestrator/metrics/exporter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Prometheus metrics exporter for orchestrator

import os
import logging
from prometheus_client import start_http_server, Gauge, Counter, Histogram
from prometheus_client.core import CollectorRegistry

from ransomeye_orchestrator.queue import JobQueue

logger = logging.getLogger(__name__)


class MetricsExporter:
    """Prometheus metrics exporter."""
    
    def __init__(self):
        """Initialize metrics exporter."""
        self.registry = CollectorRegistry()
        
        # Job metrics
        self.jobs_queued = Gauge(
            'orch_jobs_queued',
            'Number of jobs in queue',
            ['job_type', 'status'],
            registry=self.registry
        )
        
        self.jobs_total = Counter(
            'orch_jobs_total',
            'Total number of jobs processed',
            ['job_type', 'status'],
            registry=self.registry
        )
        
        # Bundle metrics
        self.bundle_size_bytes = Histogram(
            'orch_bundle_size_bytes',
            'Bundle size in bytes',
            ['compression_type'],
            registry=self.registry
        )
        
        self.bundle_duration_seconds = Histogram(
            'orch_bundle_duration_seconds',
            'Time taken to create bundle',
            ['job_type'],
            registry=self.registry
        )
        
        self.job_queue = JobQueue()
    
    def update_job_metrics(self):
        """Update job metrics from queue."""
        # This would query the database for current job counts
        # For now, we'll implement a basic version
        pass
    
    def record_bundle_size(self, size_bytes: int, compression_type: str):
        """
        Record bundle size metric.
        
        Args:
            size_bytes: Bundle size in bytes
            compression_type: Compression type (zstd, gzip)
        """
        self.bundle_size_bytes.labels(compression_type=compression_type).observe(size_bytes)
    
    def record_job_completion(self, job_type: str, status: str):
        """
        Record job completion.
        
        Args:
            job_type: Type of job
            status: Job status
        """
        self.jobs_total.labels(job_type=job_type, status=status).inc()
    
    def start_server(self, port: int = None):
        """
        Start metrics HTTP server.
        
        Args:
            port: Port to listen on (default: ORCH_METRICS_PORT env var or 9094)
        """
        if port is None:
            port = int(os.environ.get('ORCH_METRICS_PORT', '9094'))
        
        start_http_server(port, registry=self.registry)
        logger.info(f"Metrics server started on port {port}")

