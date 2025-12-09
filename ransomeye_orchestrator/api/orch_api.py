# Path and File Name : /home/ransomeye/rebuild/ransomeye_orchestrator/api/orch_api.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: FastAPI orchestrator API on port 8012

import os
import logging
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager

from ransomeye_orchestrator.queue import JobQueue, JobType
from ransomeye_orchestrator.storage import BundleStore, TempStore
from ransomeye_orchestrator.api.auth_middleware import mTLSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
job_queue = JobQueue()
bundle_store = BundleStore()
temp_store = TempStore()

# Global worker pool (will be started separately)
worker_pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager."""
    # Startup
    logger.info("Orchestrator API starting...")
    yield
    # Shutdown
    logger.info("Orchestrator API shutting down...")


app = FastAPI(
    title="RansomEye Orchestrator API",
    description="Master Flow Orchestrator & Bundler API",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add mTLS middleware (optional, can be disabled)
mtls_enabled = os.environ.get('MTLS_ENABLED', 'false').lower() == 'true'
if mtls_enabled:
    app.add_middleware(mTLSMiddleware, require_mtls=True)


# Request/Response models
class BundleCreateRequest(BaseModel):
    """Request model for bundle creation."""
    incident_id: str = Field(..., description="Incident identifier")
    priority: int = Field(100, description="Job priority")
    chunk_size_mb: int = Field(256, description="Chunk size in MB")


class RehydrateRequest(BaseModel):
    """Request model for rehydration."""
    bundle_path: str = Field(..., description="Path to bundle file")
    verify_signature: bool = Field(True, description="Verify signature")
    idempotency_key: Optional[str] = Field(None, description="Idempotency key")


class JobStatusResponse(BaseModel):
    """Job status response model."""
    job_id: str
    status: str
    created_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    error_message: Optional[str]


# API Endpoints
@app.post("/bundle/create")
async def create_bundle(request: BundleCreateRequest):
    """
    Trigger bundle creation job.
    """
    try:
        job_id = job_queue.enqueue_job(
            job_type=JobType.BUNDLE_CREATE,
            payload={
                'incident_id': request.incident_id,
                'chunk_size_mb': request.chunk_size_mb
            },
            priority=request.priority,
            idempotency_key=f"bundle_{request.incident_id}"
        )
        
        return {
            'job_id': job_id,
            'status': 'queued',
            'incident_id': request.incident_id
        }
    except Exception as e:
        logger.error(f"Failed to create bundle job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rehydrate/start")
async def start_rehydrate(
    request: RehydrateRequest,
    bundle_file: Optional[UploadFile] = File(None)
):
    """
    Upload bundle and trigger rehydration job.
    """
    try:
        bundle_path = None
        
        # If bundle file uploaded, save it
        if bundle_file:
            temp_dir = temp_store.create_temp_dir("rehydrate_")
            bundle_path = temp_dir / bundle_file.filename
            
            with open(bundle_path, 'wb') as f:
                content = await bundle_file.read()
                f.write(content)
            
            logger.info(f"Bundle uploaded: {bundle_path}")
        else:
            # Use provided path
            bundle_path = Path(request.bundle_path)
            if not bundle_path.exists():
                raise HTTPException(status_code=404, detail="Bundle file not found")
        
        # Enqueue rehydration job
        job_id = job_queue.enqueue_job(
            job_type=JobType.REHYDRATE,
            payload={
                'bundle_path': str(bundle_path),
                'verify_signature': request.verify_signature,
                'idempotency_key': request.idempotency_key
            },
            idempotency_key=request.idempotency_key or f"rehydrate_{bundle_path.stem}"
        )
        
        return {
            'job_id': job_id,
            'status': 'queued',
            'bundle_path': str(bundle_path)
        }
        
    except Exception as e:
        logger.error(f"Failed to start rehydration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get job status.
    """
    job = job_queue.get_job_status(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(
        job_id=job['job_id'],
        status=job['status'],
        created_at=job['created_at'].isoformat() if job.get('created_at') else None,
        started_at=job['started_at'].isoformat() if job.get('started_at') else None,
        completed_at=job['completed_at'].isoformat() if job.get('completed_at') else None,
        error_message=job.get('error_message')
    )


@app.get("/bundles")
async def list_bundles(incident_id: Optional[str] = None):
    """
    List bundles in store.
    """
    bundles = bundle_store.list_bundles(incident_id)
    return {'bundles': bundles}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        'status': 'healthy',
        'service': 'orchestrator',
        'port': 8012
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        'service': 'RansomEye Orchestrator API',
        'version': '1.0.0',
        'endpoints': {
            'create_bundle': '/bundle/create',
            'start_rehydrate': '/rehydrate/start',
            'get_job_status': '/jobs/{job_id}',
            'list_bundles': '/bundles'
        }
    }

