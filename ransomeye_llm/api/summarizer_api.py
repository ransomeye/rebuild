# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm/api/summarizer_api.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: FastAPI application for LLM summarizer on port 8007

import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..orchestration.summary_orchestrator import SummaryOrchestrator
from ..llm_runner.llm_infer import LLMInferenceEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
orchestrator = SummaryOrchestrator()
llm_engine = LLMInferenceEngine()

# Create FastAPI app
app = FastAPI(
    title="RansomEye LLM Summarizer API",
    description="LLM-powered incident report generation API",
    version="1.0.0"
)

# Setup metrics endpoint
from ..metrics.exporter import setup_metrics_endpoint
setup_metrics_endpoint(app)

# Request/Response models
class SummarizeRequest(BaseModel):
    """Summarize request model."""
    incident_id: str
    audience: str = "executive"  # executive, manager, analyst

class SummarizeResponse(BaseModel):
    """Summarize response model."""
    job_id: str
    status: str
    message: str

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RansomEye LLM Summarizer API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    model_available = llm_engine.is_model_available()
    return {
        "status": "healthy",
        "model_available": model_available,
        "model_path": str(llm_engine.model_path) if llm_engine.model_path else None
    }

@app.post("/summarize", response_model=SummarizeResponse)
async def summarize(request: SummarizeRequest, background_tasks: BackgroundTasks):
    """
    Start summary generation for an incident.
    
    Args:
        request: Summarize request with incident_id and audience
        background_tasks: FastAPI background tasks
        
    Returns:
        Job ID for tracking
    """
    try:
        # Validate audience
        valid_audiences = ["executive", "manager", "analyst"]
        if request.audience not in valid_audiences:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid audience. Must be one of: {valid_audiences}"
            )
        
        # Start generation (async)
        job_id = await orchestrator.generate_summary(
            incident_id=request.incident_id,
            audience=request.audience
        )
        
        return SummarizeResponse(
            job_id=job_id,
            status="pending",
            message=f"Summary generation started for incident {request.incident_id}"
        )
        
    except Exception as e:
        logger.error(f"Error starting summary generation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.get("/report/{job_id}/status")
async def get_report_status(job_id: str):
    """
    Get status of report generation job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Job status dictionary
    """
    job_status = orchestrator.get_job_status(job_id)
    
    if not job_status:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )
    
    return job_status

@app.get("/report/{job_id}/download")
async def download_report(job_id: str):
    """
    Download signed report bundle.
    
    Args:
        job_id: Job identifier
        
    Returns:
        File response with report bundle
    """
    job_status = orchestrator.get_job_status(job_id)
    
    if not job_status:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )
    
    if job_status.get('status') != 'completed':
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is not completed. Status: {job_status.get('status')}"
        )
    
    # Get report paths
    report_paths = job_status.get('report_paths', {})
    pdf_path = report_paths.get('pdf')
    
    if not pdf_path or not Path(pdf_path).exists():
        raise HTTPException(
            status_code=404,
            detail=f"Report file not found for job {job_id}"
        )
    
    # Return PDF file
    return FileResponse(
        path=pdf_path,
        filename=f"report_{job_id}.pdf",
        media_type="application/pdf"
    )

@app.get("/reports")
async def list_reports(limit: int = 100):
    """
    List all report generation jobs.
    
    Args:
        limit: Maximum number of jobs to return
        
    Returns:
        List of job dictionaries
    """
    jobs = orchestrator.list_jobs(limit=limit)
    return {
        "jobs": jobs,
        "count": len(jobs)
    }

if __name__ == "__main__":
    import uvicorn
    
    host = os.environ.get('LLM_API_HOST', '0.0.0.0')
    port = int(os.environ.get('LLM_PORT', 8007))
    
    uvicorn.run(app, host=host, port=port)

