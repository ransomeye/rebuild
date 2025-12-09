# Path and File Name : /home/ransomeye/rebuild/ransomeye_orchestrator/queue/job_queue.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Durable Postgres-backed job queue with atomic locking

import os
import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(Enum):
    """Job type enumeration."""
    BUNDLE_CREATE = "bundle_create"
    REHYDRATE = "rehydrate"


class JobQueue:
    """Durable Postgres-backed job queue with atomic locking."""
    
    def __init__(self, pool: ThreadedConnectionPool = None):
        """
        Initialize job queue.
        
        Args:
            pool: Optional connection pool. If None, creates a new one.
        """
        self.pool = pool or self._create_pool()
        self._ensure_table()
    
    def _create_pool(self) -> ThreadedConnectionPool:
        """Create database connection pool."""
        db_host = os.environ.get('DB_HOST', 'localhost')
        db_port = int(os.environ.get('DB_PORT', '5432'))
        db_name = os.environ.get('DB_NAME', 'ransomeye')
        db_user = os.environ.get('DB_USER', 'gagan')
        db_pass = os.environ.get('DB_PASS', 'gagan')
        
        return ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_pass
        )
    
    def _ensure_table(self):
        """Ensure job queue table exists."""
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orchestrator_jobs (
                    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    job_type VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    payload JSONB NOT NULL,
                    idempotency_key VARCHAR(255),
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    worker_id VARCHAR(255),
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    priority INTEGER DEFAULT 100,
                    CONSTRAINT unique_idempotency UNIQUE (idempotency_key)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_status_priority 
                ON orchestrator_jobs(status, priority DESC, created_at)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_type_status 
                ON orchestrator_jobs(job_type, status)
            """)
            
            conn.commit()
            logger.info("Job queue table ensured")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to ensure job queue table: {e}")
            raise
        finally:
            self.pool.putconn(conn)
    
    def enqueue_job(
        self,
        job_type: JobType,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        priority: int = 100,
        max_retries: int = 3
    ) -> str:
        """
        Enqueue a new job.
        
        Args:
            job_type: Type of job
            payload: Job payload data
            idempotency_key: Optional idempotency key to prevent duplicates
            priority: Job priority (higher = more important)
            max_retries: Maximum retry attempts
        
        Returns:
            Job ID (UUID string)
        """
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()
            
            job_id = str(uuid.uuid4())
            
            # If idempotency key provided, check for existing job
            if idempotency_key:
                cursor.execute("""
                    SELECT job_id, status FROM orchestrator_jobs
                    WHERE idempotency_key = %s
                """, (idempotency_key,))
                existing = cursor.fetchone()
                if existing:
                    logger.info(f"Job with idempotency key {idempotency_key} already exists: {existing[0]}")
                    return str(existing[0])
            
            cursor.execute("""
                INSERT INTO orchestrator_jobs (
                    job_id, job_type, status, payload, idempotency_key,
                    priority, max_retries
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                job_id,
                job_type.value,
                JobStatus.PENDING.value,
                json.dumps(payload),
                idempotency_key,
                priority,
                max_retries
            ))
            
            conn.commit()
            logger.info(f"Job enqueued: {job_id} (type: {job_type.value})")
            return job_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to enqueue job: {e}")
            raise
        finally:
            self.pool.putconn(conn)
    
    def fetch_next_job(self, worker_id: str, job_types: Optional[list] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch next available job with atomic locking.
        
        Uses SELECT ... FOR UPDATE SKIP LOCKED to ensure only one worker
        processes a job at a time.
        
        Args:
            worker_id: Identifier for the worker
            job_types: Optional list of job types to fetch (None = all types)
        
        Returns:
            Job dictionary or None if no jobs available
        """
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Build query with optional type filter
            if job_types:
                type_filter = "AND job_type = ANY(%s)"
                params = (JobStatus.PENDING.value, job_types, worker_id)
            else:
                type_filter = ""
                params = (JobStatus.PENDING.value, worker_id)
            
            query = f"""
                SELECT job_id, job_type, status, payload, idempotency_key,
                       created_at, retry_count, max_retries, priority
                FROM orchestrator_jobs
                WHERE status = %s {type_filter}
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            """
            
            cursor.execute(query, params)
            job_row = cursor.fetchone()
            
            if not job_row:
                return None
            
            # Update job status to processing
            cursor.execute("""
                UPDATE orchestrator_jobs
                SET status = %s, started_at = NOW(), worker_id = %s
                WHERE job_id = %s
            """, (JobStatus.PROCESSING.value, worker_id, job_row['job_id']))
            
            conn.commit()
            
            # Convert to dict
            job = dict(job_row)
            job['payload'] = json.loads(job['payload']) if isinstance(job['payload'], str) else job['payload']
            
            logger.info(f"Job fetched: {job['job_id']} by worker {worker_id}")
            return job
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to fetch job: {e}")
            raise
        finally:
            self.pool.putconn(conn)
    
    def complete_job(self, job_id: str, result: Optional[Dict[str, Any]] = None):
        """
        Mark job as completed.
        
        Args:
            job_id: Job ID
            result: Optional result data
        """
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE orchestrator_jobs
                SET status = %s, completed_at = NOW()
                WHERE job_id = %s
            """, (JobStatus.COMPLETED.value, job_id))
            conn.commit()
            logger.info(f"Job completed: {job_id}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to complete job: {e}")
            raise
        finally:
            self.pool.putconn(conn)
    
    def fail_job(self, job_id: str, error_message: str, retry: bool = True):
        """
        Mark job as failed.
        
        Args:
            job_id: Job ID
            error_message: Error message
            retry: Whether to retry if retries remaining
        """
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()
            
            # Get current retry count
            cursor.execute("""
                SELECT retry_count, max_retries FROM orchestrator_jobs
                WHERE job_id = %s
            """, (job_id,))
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"Job not found: {job_id}")
                return
            
            retry_count, max_retries = row
            
            if retry and retry_count < max_retries:
                # Retry the job
                cursor.execute("""
                    UPDATE orchestrator_jobs
                    SET status = %s, retry_count = retry_count + 1,
                        error_message = %s, started_at = NULL, worker_id = NULL
                    WHERE job_id = %s
                """, (JobStatus.PENDING.value, error_message, job_id))
                logger.info(f"Job {job_id} will be retried ({retry_count + 1}/{max_retries})")
            else:
                # Mark as permanently failed
                cursor.execute("""
                    UPDATE orchestrator_jobs
                    SET status = %s, error_message = %s, completed_at = NOW()
                    WHERE job_id = %s
                """, (JobStatus.FAILED.value, error_message, job_id))
                logger.warning(f"Job {job_id} failed permanently: {error_message}")
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to fail job: {e}")
            raise
        finally:
            self.pool.putconn(conn)
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job status.
        
        Args:
            job_id: Job ID
        
        Returns:
            Job status dictionary or None
        """
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT job_id, job_type, status, payload, created_at,
                       started_at, completed_at, worker_id, error_message,
                       retry_count, max_retries
                FROM orchestrator_jobs
                WHERE job_id = %s
            """, (job_id,))
            row = cursor.fetchone()
            
            if row:
                job = dict(row)
                job['payload'] = json.loads(job['payload']) if isinstance(job['payload'], str) else job['payload']
                return job
            return None
            
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return None
        finally:
            self.pool.putconn(conn)
    
    def cleanup_old_jobs(self, days: int = 30):
        """
        Clean up old completed/failed jobs.
        
        Args:
            days: Number of days to keep jobs
        """
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()
            cutoff = datetime.utcnow() - timedelta(days=days)
            cursor.execute("""
                DELETE FROM orchestrator_jobs
                WHERE status IN (%s, %s)
                AND completed_at < %s
            """, (JobStatus.COMPLETED.value, JobStatus.FAILED.value, cutoff))
            deleted = cursor.rowcount
            conn.commit()
            logger.info(f"Cleaned up {deleted} old jobs")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to cleanup jobs: {e}")
        finally:
            self.pool.putconn(conn)

