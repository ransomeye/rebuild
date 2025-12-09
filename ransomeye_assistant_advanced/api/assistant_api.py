# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant_advanced/api/assistant_api.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: FastAPI application for Advanced SOC Copilot with multi-modal ingestion and playbook routing on port 8008

import os
import sys
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..multi_modal.multi_modal import MultiModalOrchestrator
from ..playbook.playbook_router import PlaybookRouter
from ..storage.artifact_store import ArtifactStore
from ..storage.provenance import ProvenanceTracker
from ..feedback.feedback_collector import FeedbackCollector
from ..explain.shap_integration import SHAPIntegration
from ..metrics.exporter import setup_metrics_endpoint
from .auth_middleware import verify_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
multi_modal = MultiModalOrchestrator()
playbook_router = PlaybookRouter()
artifact_store = ArtifactStore()
provenance = ProvenanceTracker()
feedback_collector = FeedbackCollector()
shap_integration = SHAPIntegration()

# Create FastAPI app
app = FastAPI(
    title="RansomEye Advanced SOC Copilot API",
    description="Multi-modal SOC Copilot with OCR, Vision, and Intelligent Playbook Routing",
    version="2.0.0"
)

# Setup metrics endpoint
setup_metrics_endpoint(app)

# Request/Response models
class IngestRequest(BaseModel):
    """Ingest artifact request model."""
    description: Optional[str] = None
    incident_id: Optional[str] = None

class IngestResponse(BaseModel):
    """Ingest artifact response model."""
    artifact_id: str
    metadata: Dict[str, Any]
    ocr_text: Optional[str] = None
    detected_objects: Optional[List[str]] = None
    scene_description: Optional[str] = None

class SuggestPlaybookRequest(BaseModel):
    """Suggest playbook request model."""
    artifact_id: Optional[str] = None
    incident_summary: Optional[str] = None
    include_shap: bool = True

class SuggestPlaybookResponse(BaseModel):
    """Suggest playbook response model."""
    playbook_id: int
    playbook_name: str
    confidence: float
    shap_explanations: Optional[Dict[str, Any]] = None
    reasoning: str

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RansomEye Advanced SOC Copilot API",
        "version": "2.0.0",
        "status": "operational",
        "capabilities": ["OCR", "Vision", "Playbook Routing", "Multi-Modal"]
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "ocr_available": multi_modal.is_ocr_available(),
        "vision_available": multi_modal.is_vision_available(),
        "playbook_router_ready": playbook_router.is_ready()
    }

@app.post("/ingest", response_model=IngestResponse)
async def ingest_artifact(
    file: UploadFile = File(...),
    request: IngestRequest = None,
    token: str = Depends(verify_token)
):
    """
    Ingest a multi-modal artifact (Image/PDF) -> OCR -> Vision -> Store.
    
    Args:
        file: Image or PDF file to ingest
        request: Optional metadata (description, incident_id)
        
    Returns:
        Artifact ID, metadata, OCR text, detected objects, scene description
    """
    try:
        # Save uploaded file temporarily
        temp_path = Path(f"/tmp/ingest_{uuid.uuid4()}_{file.filename}")
        with open(temp_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        # Generate artifact ID
        artifact_id = str(uuid.uuid4())
        
        # Process with multi-modal pipeline
        result = multi_modal.process_artifact(temp_path, artifact_id)
        
        # Store artifact
        artifact_store.store_artifact(
            artifact_id=artifact_id,
            file_path=str(temp_path),
            mime_type=file.content_type,
            metadata={
                'filename': file.filename,
                'description': request.description if request else None,
                'incident_id': request.incident_id if request else None,
                'ocr_text': result.get('ocr_text'),
                'detected_objects': result.get('detected_objects', []),
                'scene_description': result.get('scene_description')
            }
        )
        
        # Track provenance
        if request and request.incident_id:
            provenance.link_artifact_to_incident(
                artifact_id=artifact_id,
                incident_id=request.incident_id,
                summary=result.get('scene_description', '')
            )
        
        # Cleanup temp file (after storing reference)
        # Note: Actual file stored in artifact_store
        
        logger.info(f"Ingested artifact: {artifact_id} ({file.filename})")
        
        return IngestResponse(
            artifact_id=artifact_id,
            metadata={
                'filename': file.filename,
                'mime_type': file.content_type,
                'size': len(content)
            },
            ocr_text=result.get('ocr_text'),
            detected_objects=result.get('detected_objects', []),
            scene_description=result.get('scene_description')
        )
        
    except Exception as e:
        logger.error(f"Error ingesting artifact: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.post("/suggest_playbook", response_model=SuggestPlaybookResponse)
async def suggest_playbook(
    request: SuggestPlaybookRequest,
    token: str = Depends(verify_token)
):
    """
    Suggest a playbook based on artifact or incident summary.
    
    Args:
        request: Request with artifact_id or incident_summary
        
    Returns:
        Suggested playbook with confidence and SHAP explanations
    """
    try:
        # Get context from artifact if provided
        context = None
        if request.artifact_id:
            artifact = artifact_store.get_artifact(request.artifact_id)
            if artifact:
                context = {
                    'ocr_text': artifact.get('metadata', {}).get('ocr_text'),
                    'detected_objects': artifact.get('metadata', {}).get('detected_objects', []),
                    'scene_description': artifact.get('metadata', {}).get('scene_description')
                }
        
        # Use incident summary if provided
        summary = request.incident_summary
        if not summary and context:
            summary = context.get('scene_description') or context.get('ocr_text', '')
        
        if not summary:
            raise HTTPException(
                status_code=400,
                detail="Either artifact_id or incident_summary must be provided"
            )
        
        # Route to playbook
        suggestion = playbook_router.suggest_playbook(
            summary=summary,
            context=context
        )
        
        # Generate SHAP explanations if requested
        shap_explanations = None
        if request.include_shap:
            shap_explanations = shap_integration.explain_playbook_suggestion(
                summary=summary,
                context=context,
                suggested_playbook_id=suggestion['playbook_id']
            )
        
        logger.info(f"Suggested playbook: {suggestion['playbook_id']} for summary: {summary[:50]}...")
        
        return SuggestPlaybookResponse(
            playbook_id=suggestion['playbook_id'],
            playbook_name=suggestion['playbook_name'],
            confidence=suggestion['confidence'],
            shap_explanations=shap_explanations,
            reasoning=suggestion['reasoning']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error suggesting playbook: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.post("/feedback")
async def submit_feedback(
    artifact_id: str,
    playbook_id: int,
    accepted: bool,
    comment: Optional[str] = None,
    token: str = Depends(verify_token)
):
    """
    Submit feedback on playbook suggestion.
    
    Args:
        artifact_id: Artifact ID
        playbook_id: Suggested playbook ID
        accepted: Whether suggestion was accepted
        comment: Optional comment
        
    Returns:
        Feedback submission result
    """
    try:
        feedback_collector.record_feedback(
            artifact_id=artifact_id,
            playbook_id=playbook_id,
            accepted=accepted,
            comment=comment
        )
        
        return {
            "artifact_id": artifact_id,
            "playbook_id": playbook_id,
            "status": "feedback_recorded"
        }
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str, token: str = Depends(verify_token)):
    """Get artifact metadata."""
    artifact = artifact_store.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact

if __name__ == "__main__":
    import uvicorn
    
    host = os.environ.get('ASSISTANT_API_HOST', '0.0.0.0')
    port = int(os.environ.get('ASSISTANT_API_PORT', 8008))
    
    uvicorn.run(app, host=host, port=port)

