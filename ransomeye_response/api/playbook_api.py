# Path and File Name : /home/ransomeye/rebuild/ransomeye_response/api/playbook_api.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: FastAPI application for playbook management on port 8004

import os
import sys
import tarfile
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..registry.playbook_registry import PlaybookRegistry
from ..registry.playbook_store import PlaybookStore
from ..validator.validator import PlaybookValidator
from ..validator.simulator import PlaybookSimulator
from ..executor.executor import PlaybookExecutor
from ..audit.audit_log import AuditLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
registry = PlaybookRegistry()
store = PlaybookStore()
validator = PlaybookValidator()
simulator = PlaybookSimulator()
executor = PlaybookExecutor()
audit_log = AuditLog()

# Create FastAPI app
app = FastAPI(
    title="RansomEye Incident Response API",
    description="Playbook management and execution API",
    version="1.0.0"
)

# Request/Response models
class ExecuteRequest(BaseModel):
    """Playbook execution request model."""
    playbook_id: int
    dry_run: bool = False
    context: Optional[Dict[str, Any]] = {}

class ApproveRequest(BaseModel):
    """Playbook approval request model."""
    playbook_id: int
    approved_by: str

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RansomEye Incident Response API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy"
    }

@app.post("/playbooks/upload")
async def upload_playbook(file: UploadFile = File(...)):
    """
    Upload and validate playbook bundle.
    
    Args:
        file: Playbook bundle file (.tar.gz)
        
    Returns:
        Upload result with playbook ID
    """
    try:
        # Save uploaded file temporarily
        temp_path = Path(f"/tmp/playbook_upload_{file.filename}")
        with open(temp_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        # Validate bundle
        is_valid, errors, metadata = validator.validate_bundle(temp_path)
        
        if not is_valid:
            temp_path.unlink()
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Playbook validation failed",
                    "errors": errors
                }
            )
        
        # Store bundle
        playbook_name = metadata.get('name', 'unknown')
        playbook_version = metadata.get('version', '1.0.0')
        stored_path = store.store_bundle(temp_path, playbook_name, playbook_version)
        
        # Calculate hash
        bundle_hash = store.calculate_bundle_hash(stored_path)
        
        # Register in database
        risk_level = metadata.get('risk_level', 'medium')
        playbook_id = registry.register_playbook(
            name=playbook_name,
            version=playbook_version,
            risk_level=risk_level,
            bundle_path=str(stored_path),
            manifest_hash=bundle_hash,
            metadata=metadata
        )
        
        # Cleanup temp file
        temp_path.unlink()
        
        # Log audit
        audit_log.log_event('playbook_uploaded', {
            'playbook_id': playbook_id,
            'name': playbook_name,
            'version': playbook_version,
            'risk_level': risk_level
        })
        
        return {
            "playbook_id": playbook_id,
            "name": playbook_name,
            "version": playbook_version,
            "status": "uploaded",
            "requires_approval": risk_level in ['high', 'critical']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading playbook: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.post("/playbooks/{playbook_id}/execute")
async def execute_playbook(playbook_id: int, request: ExecuteRequest):
    """
    Execute a playbook.
    
    Args:
        playbook_id: Playbook identifier
        request: Execution request with dry_run flag
        
    Returns:
        Execution result
    """
    try:
        # Get playbook
        playbook = registry.get_playbook(playbook_id)
        if not playbook:
            raise HTTPException(
                status_code=404,
                detail=f"Playbook {playbook_id} not found"
            )
        
        # Check if active
        if not playbook.get('is_active') and not request.dry_run:
            raise HTTPException(
                status_code=400,
                detail="Playbook is not active. Approval required for high-risk playbooks."
            )
        
        # Extract playbook YAML from bundle
        bundle_path = Path(playbook['bundle_path'])
        temp_dir = Path(f"/tmp/playbook_exec_{playbook_id}")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with tarfile.open(bundle_path, 'r:gz') as tar:
                tar.extractall(temp_dir)
            
            # Find playbook YAML
            playbook_yaml = None
            for yaml_file in temp_dir.glob("*.yaml"):
                playbook_yaml = yaml_file
                break
            for yaml_file in temp_dir.glob("*.yml"):
                playbook_yaml = yaml_file
                break
            
            if not playbook_yaml:
                raise HTTPException(
                    status_code=400,
                    detail="Playbook YAML not found in bundle"
                )
            
            if request.dry_run:
                # Generate execution plan
                plan = simulator.generate_execution_plan(playbook_yaml, request.context)
                return {
                    "playbook_id": playbook_id,
                    "dry_run": True,
                    "execution_plan": plan
                }
            else:
                # Execute playbook
                result = executor.execute(playbook_yaml, request.context, dry_run=False)
                
                # Log audit
                audit_log.log_event('playbook_executed', {
                    'playbook_id': playbook_id,
                    'execution_id': result.get('execution_id'),
                    'status': result.get('status'),
                    'dry_run': False
                })
                
                return result
                
        finally:
            # Cleanup
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing playbook: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.post("/playbooks/{playbook_id}/approve")
async def approve_playbook(playbook_id: int, request: ApproveRequest):
    """
    Approve a playbook (required for high-risk playbooks).
    
    Args:
        playbook_id: Playbook identifier
        request: Approval request with approver name
        
    Returns:
        Approval result
    """
    try:
        success = registry.approve_playbook(playbook_id, request.approved_by)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Playbook {playbook_id} not found"
            )
        
        # Log audit
        audit_log.log_event('playbook_approved', {
            'playbook_id': playbook_id,
            'approved_by': request.approved_by
        })
        
        return {
            "playbook_id": playbook_id,
            "status": "approved",
            "approved_by": request.approved_by
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving playbook: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.get("/playbooks")
async def list_playbooks(active_only: bool = False, limit: int = 100):
    """
    List all playbooks.
    
    Args:
        active_only: Only return active playbooks
        limit: Maximum number of playbooks to return
        
    Returns:
        List of playbooks
    """
    playbooks = registry.list_playbooks(active_only=active_only, limit=limit)
    return {
        "playbooks": playbooks,
        "count": len(playbooks)
    }

@app.get("/playbooks/{playbook_id}")
async def get_playbook(playbook_id: int):
    """
    Get playbook details.
    
    Args:
        playbook_id: Playbook identifier
        
    Returns:
        Playbook details
    """
    playbook = registry.get_playbook(playbook_id)
    if not playbook:
        raise HTTPException(
            status_code=404,
            detail=f"Playbook {playbook_id} not found"
        )
    return playbook

if __name__ == "__main__":
    import uvicorn
    
    host = os.environ.get('RESPONSE_API_HOST', '0.0.0.0')
    port = int(os.environ.get('RESPONSE_PORT', 8004))
    
    uvicorn.run(app, host=host, port=port)

