# Path and File Name : /home/ransomeye/rebuild/ransomeye_orchestrator/queue/worker_pool.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Async worker pool manager that polls queue and dispatches jobs

import os
import asyncio
import logging
import uuid
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from ransomeye_orchestrator.queue.job_queue import JobQueue, JobType
from ransomeye_orchestrator.bundle.bundle_builder import BundleBuilder
from ransomeye_orchestrator.rehydrate.rebuild_incident import RebuildIncident

logger = logging.getLogger(__name__)


class WorkerPool:
    """Async worker pool manager that polls queue and dispatches jobs."""
    
    def __init__(self, num_workers: int = 4):
        """
        Initialize worker pool.
        
        Args:
            num_workers: Number of concurrent workers
        """
        self.num_workers = num_workers
        self.job_queue = JobQueue()
        self.bundle_builder = BundleBuilder()
        self.rebuild_incident = RebuildIncident()
        self.executor = ThreadPoolExecutor(max_workers=num_workers)
        self.workers = []
        self.running = False
    
    async def start(self):
        """Start worker pool."""
        if self.running:
            logger.warning("Worker pool already running")
            return
        
        self.running = True
        logger.info(f"Starting worker pool with {self.num_workers} workers")
        
        # Start worker tasks
        for i in range(self.num_workers):
            worker_id = f"worker-{uuid.uuid4().hex[:8]}"
            task = asyncio.create_task(self._worker_loop(worker_id))
            self.workers.append(task)
        
        logger.info("Worker pool started")
    
    async def stop(self):
        """Stop worker pool."""
        if not self.running:
            return
        
        logger.info("Stopping worker pool...")
        self.running = False
        
        # Wait for all workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.info("Worker pool stopped")
    
    async def _worker_loop(self, worker_id: str):
        """Worker loop that polls queue and processes jobs."""
        logger.info(f"Worker {worker_id} started")
        
        while self.running:
            try:
                # Poll for jobs
                job = await asyncio.to_thread(
                    self.job_queue.fetch_next_job,
                    worker_id
                )
                
                if job:
                    # Process job in thread pool
                    await asyncio.get_event_loop().run_in_executor(
                        self.executor,
                        self._process_job,
                        worker_id,
                        job
                    )
                else:
                    # No jobs available, wait before polling again
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(5)  # Wait before retrying
        
        logger.info(f"Worker {worker_id} stopped")
    
    def _process_job(self, worker_id: str, job: dict):
        """
        Process a job.
        
        Args:
            worker_id: Worker identifier
            job: Job dictionary
        """
        job_id = job['job_id']
        job_type = job['job_type']
        payload = job['payload']
        
        logger.info(f"Worker {worker_id} processing job {job_id} (type: {job_type})")
        
        try:
            if job_type == JobType.BUNDLE_CREATE.value:
                result = self.bundle_builder.create_bundle(
                    incident_id=payload.get('incident_id'),
                    output_path=payload.get('output_path'),
                    chunk_size_mb=payload.get('chunk_size_mb', 256)
                )
                self.job_queue.complete_job(job_id, result)
                logger.info(f"Job {job_id} completed successfully")
                
            elif job_type == JobType.REHYDRATE.value:
                result = self.rebuild_incident.rehydrate(
                    bundle_path=payload.get('bundle_path'),
                    verify_signature=payload.get('verify_signature', True),
                    idempotency_key=payload.get('idempotency_key')
                )
                self.job_queue.complete_job(job_id, result)
                logger.info(f"Job {job_id} completed successfully")
                
            else:
                error_msg = f"Unknown job type: {job_type}"
                logger.error(error_msg)
                self.job_queue.fail_job(job_id, error_msg, retry=False)
                
        except Exception as e:
            error_msg = f"Job processing failed: {str(e)}"
            logger.error(f"Job {job_id} failed: {error_msg}", exc_info=True)
            self.job_queue.fail_job(job_id, error_msg, retry=True)

