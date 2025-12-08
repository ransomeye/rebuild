# Path and File Name : /home/ransomeye/rebuild/ransomeye_killchain/api/timeline_api.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: FastAPI application for KillChain timeline management on port 8005

import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..engine.timeline_builder import TimelineBuilder
from ..engine.mitre_mapper import MitreMapper
from ..engine.graph_exporter import GraphExporter
from ..storage.timeline_store import TimelineStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
timeline_builder = TimelineBuilder()
mitre_mapper = MitreMapper()
graph_exporter = GraphExporter()
timeline_store = TimelineStore()

# Create FastAPI app
app = FastAPI(
    title="RansomEye KillChain API",
    description="Attack timeline and MITRE mapping API",
    version="1.0.0"
)

# Request/Response models
class AlertData(BaseModel):
    """Alert data model."""
    source: str
    alert_type: str
    target: str
    severity: Optional[str] = "medium"
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

class TimelineRequest(BaseModel):
    """Timeline build request model."""
    incident_id: str
    alerts: List[AlertData]

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RansomEye KillChain API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "mitre_data_loaded": mitre_mapper.mitre_data is not None
    }

@app.post("/timeline/build")
async def build_timeline(request: TimelineRequest):
    """
    Build timeline from alerts.
    
    Args:
        request: Timeline build request with alerts
        
    Returns:
        Timeline with MITRE mappings and graph
    """
    try:
        # Convert alerts to dictionaries
        alerts = [alert.dict() for alert in request.alerts]
        
        # Build timeline
        timeline = timeline_builder.build_timeline(
            alerts=alerts,
            incident_id=request.incident_id
        )
        
        # Map to MITRE TTPs
        timeline = mitre_mapper.map_timeline(timeline)
        
        # Export graph
        graph = graph_exporter.export_graph(timeline)
        
        # Save to database
        timeline_id = timeline_store.save_timeline(
            incident_id=request.incident_id,
            timeline=timeline,
            graph=graph
        )
        
        return {
            "timeline_id": timeline_id,
            "incident_id": request.incident_id,
            "timeline": timeline,
            "graph": graph
        }
        
    except Exception as e:
        logger.error(f"Error building timeline: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.get("/timeline/{incident_id}")
async def get_timeline(incident_id: str):
    """
    Get timeline by incident ID.
    
    Args:
        incident_id: Incident identifier
        
    Returns:
        Timeline data
    """
    try:
        timeline_data = timeline_store.get_timeline(incident_id)
        
        if not timeline_data:
            raise HTTPException(
                status_code=404,
                detail=f"Timeline for incident {incident_id} not found"
            )
        
        return timeline_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting timeline: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.get("/timeline/{incident_id}/graph")
async def get_timeline_graph(incident_id: str):
    """
    Get graph representation of timeline.
    
    Args:
        incident_id: Incident identifier
        
    Returns:
        Graph data
    """
    try:
        timeline_data = timeline_store.get_timeline(incident_id)
        
        if not timeline_data:
            raise HTTPException(
                status_code=404,
                detail=f"Timeline for incident {incident_id} not found"
            )
        
        graph = timeline_data.get('graph')
        if not graph:
            # Rebuild graph if not stored
            timeline = timeline_data.get('timeline')
            if timeline:
                graph = graph_exporter.export_graph(timeline)
            else:
                raise HTTPException(
                    status_code=404,
                    detail="Graph data not available"
                )
        
        return graph
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting graph: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.get("/mitre/ttp/{ttp_id}")
async def get_ttp_info(ttp_id: str):
    """
    Get MITRE TTP information.
    
    Args:
        ttp_id: MITRE TTP ID (e.g., "T1110")
        
    Returns:
        TTP information
    """
    try:
        ttp_info = mitre_mapper.get_ttp_info(ttp_id)
        
        if not ttp_info:
            raise HTTPException(
                status_code=404,
                detail=f"MITRE TTP {ttp_id} not found"
            )
        
        return ttp_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting TTP info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.get("/timelines")
async def list_timelines(limit: int = 100):
    """
    List all timelines.
    
    Args:
        limit: Maximum number of timelines to return
        
    Returns:
        List of timelines
    """
    try:
        timelines = timeline_store.list_timelines(limit=limit)
        return {
            "timelines": timelines,
            "count": len(timelines)
        }
    except Exception as e:
        logger.error(f"Error listing timelines: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    
    host = os.environ.get('KILLCHAIN_API_HOST', '0.0.0.0')
    port = int(os.environ.get('KILLCHAIN_PORT', 8005))
    
    uvicorn.run(app, host=host, port=port)

