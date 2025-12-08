# Path and File Name : /home/ransomeye/rebuild/ransomeye_correlation/api/correlation_api.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: FastAPI application for Threat Correlation Engine on port 8011

import os
import sys
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..engine.entity_extractor import EntityExtractor
from ..engine.graph_builder import GraphBuilder
from ..engine.graph_store import GraphStore
from ..engine.neo4j_exporter import Neo4jExporter
from ..ml.confidence_predictor import ConfidencePredictor
from ..ml.shap_explainer import SHAPExplainer
from ..storage.incident_store import IncidentStore
from ..storage.artifact_buffer import ArtifactBuffer
from ..storage.manifest_signer import ManifestSigner
from ..metrics.exporter import setup_metrics_endpoint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
entity_extractor = EntityExtractor()
graph_builder = GraphBuilder()
graph_store = GraphStore()
neo4j_exporter = Neo4jExporter()
confidence_predictor = ConfidencePredictor()
shap_explainer = SHAPExplainer()
incident_store = IncidentStore()
artifact_buffer = ArtifactBuffer()
manifest_signer = ManifestSigner()

# Create FastAPI app
app = FastAPI(
    title="RansomEye Threat Correlation Engine API",
    description="Graph-based threat correlation with ML confidence scoring",
    version="1.0.0"
)

# Setup metrics endpoint
setup_metrics_endpoint(app)

# Request/Response models
class AlertIngestRequest(BaseModel):
    """Alert ingestion request model."""
    alerts: List[Dict[str, Any]]

class IncidentResponse(BaseModel):
    """Incident response model."""
    incident_id: str
    graph: Dict[str, Any]
    confidence_score: float
    shap_explanation: Optional[Dict[str, Any]] = None

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RansomEye Threat Correlation Engine API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "graph_store_ready": graph_store.is_connected(),
        "confidence_model_loaded": confidence_predictor.is_model_loaded()
    }

@app.post("/ingest")
async def ingest_alerts(request: AlertIngestRequest):
    """
    Accepts batch of alerts -> Extractor -> Graph Builder.
    
    Args:
        request: Alert ingestion request
        
    Returns:
        Ingestion result
    """
    try:
        # Buffer alerts
        artifact_buffer.add_alerts(request.alerts)
        
        # Process alerts
        processed_count = 0
        for alert in request.alerts:
            # Extract entities
            entities = entity_extractor.extract(alert)
            
            # Add to graph
            graph_builder.add_entities(entities, alert)
            
            processed_count += 1
        
        # Persist graph state
        graph_store.save_graph(graph_builder.get_graph_state())
        
        # Correlate incidents
        incidents = graph_builder.correlate_incidents()
        
        # Store incidents
        for incident in incidents:
            incident_store.create_incident(incident)
        
        logger.info(f"Ingested {processed_count} alerts, created {len(incidents)} incidents")
        
        return {
            "alerts_processed": processed_count,
            "incidents_created": len(incidents),
            "status": "ingested"
        }
        
    except Exception as e:
        logger.error(f"Error ingesting alerts: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.get("/incident/{incident_id}", response_model=IncidentResponse)
async def get_incident(incident_id: str):
    """
    Returns graph JSON + Score + SHAP.
    
    Args:
        incident_id: Incident identifier
        
    Returns:
        Incident with graph, confidence score, and SHAP explanation
    """
    try:
        # Get incident
        incident = incident_store.get_incident(incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        # Get graph for incident
        graph_data = graph_store.get_incident_graph(incident_id)
        
        # Calculate confidence score
        confidence_score = confidence_predictor.predict(graph_data)
        
        # Generate SHAP explanation
        shap_explanation = shap_explainer.explain(graph_data, confidence_score)
        
        return IncidentResponse(
            incident_id=incident_id,
            graph=graph_data,
            confidence_score=confidence_score,
            shap_explanation=shap_explanation
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting incident: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.get("/export/{incident_id}")
async def export_incident(incident_id: str):
    """
    Returns signed .tar.gz bundle for Neo4j.
    
    Args:
        incident_id: Incident identifier
        
    Returns:
        Signed export bundle
    """
    try:
        # Verify incident exists
        incident = incident_store.get_incident(incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        # Export to Neo4j format
        export_path = neo4j_exporter.export_incident(incident_id)
        
        # Sign the export
        signed_bundle_path = manifest_signer.sign_export(export_path, incident_id)
        
        # Return file
        return FileResponse(
            path=str(signed_bundle_path),
            filename=f"incident_{incident_id}_export.tar.gz",
            media_type="application/gzip"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting incident: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.get("/incidents")
async def list_incidents():
    """List all incidents."""
    try:
        incidents = incident_store.list_incidents()
        return {"incidents": incidents}
    except Exception as e:
        logger.error(f"Error listing incidents: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/stats")
async def get_stats():
    """Get graph statistics."""
    try:
        stats = graph_store.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    host = os.environ.get('CORRELATION_API_HOST', '0.0.0.0')
    port = int(os.environ.get('CORRELATION_PORT', 8011))
    
    uvicorn.run(app, host=host, port=port)

