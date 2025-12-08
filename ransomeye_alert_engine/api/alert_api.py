# Path and File Name : /home/ransomeye/rebuild/ransomeye_alert_engine/api/alert_api.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: FastAPI application for alert ingestion and policy management

import os
import sys
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..evaluator.policy_evaluator import PolicyEvaluator
from ..dedupe.duplicate_filter import DuplicateFilter
from ..storage.alert_buffer import AlertBuffer
from ..loader.policy_loader import get_policy_loader
from .policy_api import router as policy_router
from ..metrics.exporter import start_metrics_server
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
evaluator = PolicyEvaluator()
duplicate_filter = DuplicateFilter()
alert_buffer = AlertBuffer()
policy_loader = get_policy_loader()

# Create FastAPI app
app = FastAPI(
    title="RansomEye Alert Engine API",
    description="Alert ingestion and policy management API",
    version="1.0.0"
)

# Include policy API router
app.include_router(policy_router)

# Request/Response models
class AlertRequest(BaseModel):
    """Alert ingestion request model."""
    source: str
    alert_type: str
    target: str
    severity: Optional[str] = "medium"
    metadata: Optional[Dict[str, Any]] = {}
    timestamp: Optional[str] = None

class AlertResponse(BaseModel):
    """Alert ingestion response model."""
    alert_id: str
    status: str
    is_duplicate: bool
    matches: list

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RansomEye Alert Engine API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    policy_info = policy_loader.get_active_policy_info()
    return {
        "status": "healthy",
        "policy_loaded": policy_info['loaded'],
        "policy_version": policy_info.get('version', 'unknown'),
        "rules_count": policy_info.get('rules_count', 0)
    }

@app.post("/alerts/ingest")
async def ingest_alert(alert: AlertRequest):
    """
    Ingest a new alert and evaluate against active policies.
    
    Args:
        alert: Alert data
        
    Returns:
        Alert ID and evaluation results
    """
    try:
        # Generate alert ID
        alert_id = str(uuid.uuid4())
        
        # Check for duplicates
        is_duplicate, duplicate_type = duplicate_filter.check_duplicate(
            source=alert.source,
            alert_type=alert.alert_type,
            target=alert.target,
            metadata=alert.metadata
        )
        
        if is_duplicate:
            logger.info(f"Alert {alert_id} flagged as duplicate ({duplicate_type})")
            return {
                "alert_id": alert_id,
                "status": "duplicate",
                "is_duplicate": True,
                "duplicate_type": duplicate_type,
                "matches": []
            }
        
        # Evaluate against policies
        matches = evaluator.evaluate_alert(
            source=alert.source,
            alert_type=alert.alert_type,
            target=alert.target,
            severity=alert.severity,
            metadata=alert.metadata
        )
        
        # Buffer alert for async write
        alert_data = {
            "alert_id": alert_id,
            "source": alert.source,
            "alert_type": alert.alert_type,
            "target": alert.target,
            "severity": alert.severity,
            "metadata": alert.metadata,
            "matches": matches,
            "timestamp": alert.timestamp
        }
        alert_buffer.buffer_alert(alert_data)
        
        logger.info(f"Alert {alert_id} ingested with {len(matches)} matches")
        
        return {
            "alert_id": alert_id,
            "status": "processed",
            "is_duplicate": False,
            "matches": matches
        }
        
    except Exception as e:
        logger.error(f"Error ingesting alert: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.post("/policies/upload")
async def upload_policy(
    file: UploadFile = File(...)
):
    """
    Upload and load a new policy bundle.
    
    Args:
        file: Policy bundle file (.tar.gz)
        
    Returns:
        Policy loading status
    """
    try:
        # Validate file type
        if not file.filename.endswith('.tar.gz'):
            raise HTTPException(
                status_code=400,
                detail="File must be a .tar.gz bundle"
            )
        
        # Save uploaded file temporarily
        temp_path = Path(f"/tmp/{file.filename}")
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(temp_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        # Load policy bundle
        try:
            result = policy_loader.load_policy_bundle(temp_path)
            
            # Clean up temp file
            temp_path.unlink()
            
            return {
                "status": "loaded",
                "policy_version": result.get('version', 'unknown'),
                "rules_count": result.get('rules_count', 0),
                "message": "Policy bundle loaded successfully"
            }
            
        except Exception as e:
            # Clean up on failure
            if temp_path.exists():
                temp_path.unlink()
            raise HTTPException(
                status_code=400,
                detail=f"Policy validation/loading failed: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading policy: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    
    # Start metrics server
    try:
        start_metrics_server()
    except Exception as e:
        logger.warning(f"Failed to start metrics server: {e}")
    
    host = os.environ.get('ALERT_ENGINE_HOST', '0.0.0.0')
    port = int(os.environ.get('ALERT_ENGINE_PORT', 8000))
    
    uvicorn.run(app, host=host, port=port)

