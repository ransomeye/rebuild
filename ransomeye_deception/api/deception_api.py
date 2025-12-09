# Path and File Name : /home/ransomeye/rebuild/ransomeye_deception/api/deception_api.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: FastAPI application for Deception Framework on port 8010

import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..dispatcher import Dispatcher
from ..simulator.attacker_simulator import AttackerSimulator
from ..storage.config_store import ConfigStore
from ..metrics.exporter import setup_metrics_endpoint, start_metrics_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
dispatcher = Dispatcher()
simulator = AttackerSimulator()
config_store = ConfigStore()

# Create FastAPI app
app = FastAPI(
    title="RansomEye Deception Framework API",
    description="AI-driven decoy deployment and rotation framework",
    version="1.0.0"
)

# Setup metrics endpoint
setup_metrics_endpoint(app)

# Request/Response models
class DeployRequest(BaseModel):
    """Deploy decoy request model."""
    decoy_type: str  # file, service, process, host
    target_location: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

class DeployResponse(BaseModel):
    """Deploy decoy response model."""
    decoy_id: str
    type: str
    location: str
    status: str

class RotateRequest(BaseModel):
    """Rotate decoy request model."""
    decoy_id: Optional[str] = None  # If None, rotate all

class SimulateRequest(BaseModel):
    """Simulate attack request model."""
    decoy_type: str
    target: str
    duration_seconds: int = 60

class StatusResponse(BaseModel):
    """Status response model."""
    total_decoys: int
    by_type: Dict[str, int]
    decoys: List[Dict[str, Any]]


@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    # Start metrics server on separate port
    try:
        start_metrics_server()
    except Exception as e:
        logger.warning(f"Failed to start metrics server: {e}")
    
    await dispatcher.start()
    logger.info("Deception API started")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    await dispatcher.stop()
    logger.info("Deception API stopped")


@app.post("/deploy", response_model=DeployResponse)
async def deploy_decoy(request: DeployRequest):
    """
    Deploy a new decoy.
    
    Args:
        request: Deploy request
        
    Returns:
        Deployment result
    """
    try:
        result = await dispatcher.deploy_decoy(
            decoy_type=request.decoy_type,
            target_location=request.target_location,
            metadata=request.metadata
        )
        
        return DeployResponse(
            decoy_id=result['decoy_id'],
            type=result['type'],
            location=result['location'],
            status=result['status']
        )
    except Exception as e:
        logger.error(f"Error deploying decoy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rotate")
async def rotate_decoy(request: RotateRequest, background_tasks: BackgroundTasks):
    """
    Rotate decoy(s).
    
    Args:
        request: Rotate request
        background_tasks: Background tasks
        
    Returns:
        Rotation result
    """
    try:
        if request.decoy_id:
            # Rotate specific decoy
            result = await dispatcher.rotate_decoy(request.decoy_id)
            return result
        else:
            # Rotate all decoys in background
            async def rotate_all():
                active_decoys = await config_store.get_active_decoys()
                for decoy in active_decoys:
                    try:
                        await dispatcher.rotate_decoy(decoy['id'])
                    except Exception as e:
                        logger.error(f"Error rotating decoy {decoy['id']}: {e}")
            
            background_tasks.add_task(rotate_all)
            return {"status": "started", "message": "Rotation started for all decoys"}
            
    except Exception as e:
        logger.error(f"Error rotating decoy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/simulate")
async def simulate_attack(request: SimulateRequest):
    """
    Run attacker simulation.
    
    Args:
        request: Simulate request
        
    Returns:
        Simulation results
    """
    try:
        result = await simulator.simulate_attack(
            decoy_type=request.decoy_type,
            target=request.target,
            duration_seconds=request.duration_seconds
        )
        return result
    except Exception as e:
        logger.error(f"Error simulating attack: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """
    Get deployment status.
    
    Returns:
        Current deployment status
    """
    try:
        status = await dispatcher.get_deployment_status()
        return StatusResponse(**status)
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "deception_framework"
    }

