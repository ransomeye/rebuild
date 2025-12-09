# Path and File Name : /home/ransomeye/rebuild/ransomeye_global_validator/api/validator_api.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: FastAPI application for validation run management on port 8100

import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..validator.synthetic_runner import SyntheticRunner
from ..storage.run_store import RunStore
from ..chain.manifest_verifier import ManifestVerifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
runner = SyntheticRunner()
run_store = RunStore()
manifest_verifier = ManifestVerifier()

# Create FastAPI app
app = FastAPI(
    title="RansomEye Global Validator API",
    description="Validation run management and reporting API",
    version="1.0.0"
)

# Request/Response models
class ValidationRequest(BaseModel):
    """Validation run request model."""
    scenario_type: str = "happy_path"
    scenario_config: Optional[Dict[str, Any]] = None

class ValidationResponse(BaseModel):
    """Validation run response model."""
    run_id: str
    status: str
    message: str

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RansomEye Global Validator API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "runner_ready": True,
        "run_store_ready": True
    }

@app.post("/runs", response_model=ValidationResponse)
async def trigger_validation(request: ValidationRequest):
    """
    Trigger a validation run.
    
    Args:
        request: Validation request
        
    Returns:
        Validation run response
    """
    try:
        # Run validation
        run_data = await runner.run_validation(
            scenario_type=request.scenario_type,
            scenario_config=request.scenario_config
        )
        
        return ValidationResponse(
            run_id=run_data.get("run_id"),
            status="completed",
            message="Validation run completed successfully"
        )
    
    except Exception as e:
        logger.error(f"Validation trigger error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(e)}"
        )

@app.get("/runs/{run_id}")
async def get_run(run_id: str):
    """
    Get validation run data.
    
    Args:
        run_id: Run identifier
        
    Returns:
        Run data
    """
    run_data = run_store.get_run(run_id)
    
    if not run_data:
        raise HTTPException(
            status_code=404,
            detail=f"Run {run_id} not found"
        )
    
    return run_data

@app.get("/runs/{run_id}/report")
async def download_report(run_id: str):
    """
    Download PDF validation report.
    
    Args:
        run_id: Run identifier
        
    Returns:
        PDF file
    """
    pdf_path = run_store.get_pdf_path(run_id)
    
    if not Path(pdf_path).exists():
        raise HTTPException(
            status_code=404,
            detail=f"Report for run {run_id} not found"
        )
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"validation_report_{run_id}.pdf"
    )

@app.get("/runs/{run_id}/manifest")
async def get_manifest(run_id: str):
    """
    Get validation run manifest.
    
    Args:
        run_id: Run identifier
        
    Returns:
        Manifest data
    """
    manifest_path = run_store.get_manifest_path(run_id).replace('.json', '.signed.json')
    
    if not Path(manifest_path).exists():
        raise HTTPException(
            status_code=404,
            detail=f"Manifest for run {run_id} not found"
        )
    
    import json
    with open(manifest_path, 'r') as f:
        manifest_data = json.load(f)
    
    return manifest_data

@app.get("/runs/{run_id}/verify")
async def verify_run(run_id: str):
    """
    Verify validation run chain of custody.
    
    Args:
        run_id: Run identifier
        
    Returns:
        Verification result
    """
    run_store_path = os.environ.get(
        'VALIDATOR_RUN_STORE_PATH',
        '/home/ransomeye/rebuild/ransomeye_global_validator/storage/runs'
    )
    
    result = manifest_verifier.verify_chain(run_id, run_store_path)
    return result

@app.get("/runs")
async def list_runs(limit: int = 100):
    """
    List validation runs.
    
    Args:
        limit: Maximum number of runs to return
        
    Returns:
        List of runs
    """
    runs = run_store.list_runs(limit=limit)
    return {
        "runs": runs,
        "count": len(runs)
    }

if __name__ == "__main__":
    import uvicorn
    
    host = os.environ.get('VALIDATOR_API_HOST', '0.0.0.0')
    port = int(os.environ.get('VALIDATOR_API_PORT', 8100))
    
    uvicorn.run(app, host=host, port=port)

