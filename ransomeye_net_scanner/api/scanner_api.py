# Path and File Name : /home/ransomeye/rebuild/ransomeye_net_scanner/api/scanner_api.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: FastAPI application for Network Scanner on port 8102

import os
import sys
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..engine.active_scanner import ActiveScanner
from ..engine.passive_listener import PassiveListener
from ..engine.asset_manager import AssetManager
from ..engine.scheduler import ScanScheduler
from ..topology.graph_builder import TopologyGraphBuilder
from ..topology.topology_exporter import TopologyExporter
from ..storage.asset_db import AssetDB
from ..storage.scan_store import ScanStore
from ..metrics.exporter import setup_metrics_endpoint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
active_scanner = ActiveScanner()
passive_listener = PassiveListener()
asset_manager = AssetManager()
scheduler = ScanScheduler()
graph_builder = TopologyGraphBuilder()
topology_exporter = TopologyExporter()
asset_db = AssetDB()
scan_store = ScanStore()

# Create FastAPI app
app = FastAPI(
    title="RansomEye Network Scanner API",
    description="Active and passive network scanning with offline CVE matching",
    version="1.0.0"
)

# Setup metrics endpoint
setup_metrics_endpoint(app)

# Request/Response models
class ScanRequest(BaseModel):
    """Scan request model."""
    subnets: List[str]
    scan_type: str = "active"  # active, passive, both
    intensity: str = "T3"  # T1-T5

class TopologyResponse(BaseModel):
    """Topology response model."""
    nodes: List[Dict[str, Any]]
    links: List[Dict[str, Any]]

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RansomEye Network Scanner API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "passive_listener_running": passive_listener.is_running(),
        "nmap_available": active_scanner.is_nmap_available(),
        "cve_db_loaded": asset_manager.is_cve_db_loaded()
    }

@app.post("/scan/start")
async def start_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    """
    Trigger active scan on subnets.
    
    Args:
        request: Scan request with subnets
        background_tasks: FastAPI background tasks
        
    Returns:
        Scan job ID
    """
    try:
        scan_id = str(uuid.uuid4())
        
        # Start scan in background
        background_tasks.add_task(
            _run_scan,
            scan_id,
            request.subnets,
            request.scan_type,
            request.intensity
        )
        
        return {
            "scan_id": scan_id,
            "status": "started",
            "subnets": request.subnets
        }
        
    except Exception as e:
        logger.error(f"Error starting scan: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

def _run_scan(scan_id: str, subnets: List[str], scan_type: str, intensity: str):
    """Run scan in background."""
    try:
        results = []
        
        if scan_type in ["active", "both"]:
            # Run active scan
            for subnet in subnets:
                scan_result = active_scanner.scan_subnet(subnet, intensity)
                results.append(scan_result)
                
                # Store scan results
                scan_store.save_scan(scan_id, subnet, scan_result)
                
                # Update asset database
                asset_manager.process_scan_results(scan_result)
        
        if scan_type in ["passive", "both"]:
            # Passive scanning is continuous, just ensure listener is running
            if not passive_listener.is_running():
                passive_listener.start()
        
        logger.info(f"Scan {scan_id} completed: {len(results)} subnets scanned")
        
    except Exception as e:
        logger.error(f"Error running scan {scan_id}: {e}", exc_info=True)

@app.get("/topology", response_model=TopologyResponse)
async def get_topology():
    """
    Return Nodes/Edges for UI.
    
    Returns:
        Topology graph with nodes and links
    """
    try:
        # Build graph from assets
        graph = graph_builder.build_graph()
        
        # Export to JSON format
        topology = topology_exporter.export_graph(graph)
        
        return TopologyResponse(
            nodes=topology.get('nodes', []),
            links=topology.get('links', [])
        )
        
    except Exception as e:
        logger.error(f"Error getting topology: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.get("/assets")
async def get_assets():
    """
    List inventory.
    
    Returns:
        List of assets
    """
    try:
        assets = asset_db.list_assets()
        return {
            "assets": assets,
            "total": len(assets)
        }
    except Exception as e:
        logger.error(f"Error getting assets: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/assets/{asset_id}")
async def get_asset(asset_id: str):
    """Get asset details."""
    try:
        asset = asset_db.get_asset(asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        return asset
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting asset: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/scans")
async def list_scans():
    """List all scans."""
    try:
        scans = scan_store.list_scans()
        return {"scans": scans}
    except Exception as e:
        logger.error(f"Error listing scans: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/stats")
async def get_stats():
    """Get scanner statistics."""
    try:
        stats = asset_db.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    host = os.environ.get('NETSCANNER_API_HOST', '0.0.0.0')
    port = int(os.environ.get('NETSCANNER_API_PORT', 8102))
    
    uvicorn.run(app, host=host, port=port)

