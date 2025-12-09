# Path and File Name : /home/ransomeye/rebuild/ransomeye_orchestrator/orchestrator_service.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Main orchestrator service that starts API and worker pool

import os
import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager

import uvicorn
from ransomeye_orchestrator.queue import WorkerPool
from ransomeye_orchestrator.metrics import MetricsExporter
from ransomeye_orchestrator.api import app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global references
worker_pool = None
metrics_exporter = None


async def startup():
    """Startup tasks."""
    global worker_pool, metrics_exporter
    
    logger.info("Starting RansomEye Orchestrator Service...")
    
    # Start metrics exporter
    metrics_exporter = MetricsExporter()
    metrics_port = int(os.environ.get('ORCH_METRICS_PORT', '9094'))
    metrics_exporter.start_server(metrics_port)
    logger.info(f"Metrics server started on port {metrics_port}")
    
    # Start worker pool
    num_workers = int(os.environ.get('ORCH_WORKER_COUNT', '4'))
    worker_pool = WorkerPool(num_workers=num_workers)
    await worker_pool.start()
    logger.info(f"Worker pool started with {num_workers} workers")
    
    logger.info("Orchestrator service started successfully")


async def shutdown():
    """Shutdown tasks."""
    global worker_pool
    
    logger.info("Shutting down RansomEye Orchestrator Service...")
    
    if worker_pool:
        await worker_pool.stop()
    
    logger.info("Orchestrator service stopped")


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    logger.info("Received shutdown signal")
    asyncio.create_task(shutdown())
    sys.exit(0)


async def main():
    """Main service loop."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Startup
    await startup()
    
    # Start API server
    api_port = int(os.environ.get('ORCH_API_PORT', '8012'))
    api_host = os.environ.get('ORCH_API_HOST', '0.0.0.0')
    
    config = uvicorn.Config(
        app,
        host=api_host,
        port=api_port,
        log_level="info"
    )
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Server interrupted")
    finally:
        await shutdown()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service interrupted")
    except Exception as e:
        logger.error(f"Service error: {e}", exc_info=True)
        sys.exit(1)

