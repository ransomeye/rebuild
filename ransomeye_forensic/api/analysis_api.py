# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/api/analysis_api.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: FastAPI endpoints for memory diffing, DNA extraction, classification, and feedback

import os
import sys
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..diff.diff_memory import MemoryDiffer
from ..dna.malware_dna import MalwareDNAExtractor
from ..dna.sequence_extractor import SequenceExtractor
from ..dna.dna_serializer import DNASerializer
from ..dna.yara_wrapper import YARAWrapper
from ..ml.inference.classifier import ForensicClassifier
from ..ml.inference.fingerprinter import DNAFingerprinter
from ..ml.trainer.incremental_trainer import IncrementalTrainer
from ..storage.artifact_store import ArtifactStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
memory_differ = MemoryDiffer()
dna_extractor = MalwareDNAExtractor()
sequence_extractor = SequenceExtractor()
dna_serializer = DNASerializer()
yara_wrapper = YARAWrapper()
classifier = ForensicClassifier()
fingerprinter = DNAFingerprinter()
artifact_store = ArtifactStore()

# Create router
router = APIRouter(prefix="/analysis", tags=["analysis"])

# Request/Response models
class DiffRequest(BaseModel):
    """Memory diff request model."""
    snapshot_a: str  # Artifact ID or path
    snapshot_b: str  # Artifact ID or path
    snapshot_a_id: Optional[str] = None
    snapshot_b_id: Optional[str] = None

class DiffResponse(BaseModel):
    """Memory diff response model."""
    diff_id: str
    statistics: Dict[str, Any]
    changed_pages: List[Dict]
    added_pages: List[Dict]
    removed_pages: List[Dict]

class DNAExtractRequest(BaseModel):
    """DNA extraction request model."""
    artifact_id: str
    artifact_path: Optional[str] = None
    artifact_type: str = "binary"

class DNAExtractResponse(BaseModel):
    """DNA extraction response model."""
    dna_id: str
    dna_hash: str
    dna_data: Dict[str, Any]
    classification: Dict[str, Any]
    yara_matches: List[Dict]
    fingerprint: Dict[str, Any]

class FeedbackRequest(BaseModel):
    """Feedback request model."""
    dna_id: str
    dna_data: Dict[str, Any]
    predicted_label: bool
    operator_label: bool
    operator_notes: Optional[str] = None

class FeedbackResponse(BaseModel):
    """Feedback response model."""
    feedback_id: str
    status: str
    update_triggered: bool

@router.post("/diff", response_model=DiffResponse)
async def diff_memory(request: DiffRequest):
    """
    Compare two memory snapshots and return diff results.
    
    Args:
        request: Diff request with snapshot IDs/paths
        
    Returns:
        Diff results with changed pages and statistics
    """
    try:
        # Resolve snapshot paths
        snapshot_a_path = request.snapshot_a
        snapshot_b_path = request.snapshot_b
        
        # If artifact IDs, resolve from store
        if not Path(snapshot_a_path).exists():
            # Try as artifact ID - check if directory exists
            artifact_dir_a = artifact_store.get_artifact_dir(request.snapshot_a)
            snapshot_file_a = artifact_dir_a / "snapshot.raw"
            if snapshot_file_a.exists():
                snapshot_a_path = str(snapshot_file_a)
        
        if not Path(snapshot_b_path).exists():
            artifact_dir_b = artifact_store.get_artifact_dir(request.snapshot_b)
            snapshot_file_b = artifact_dir_b / "snapshot.raw"
            if snapshot_file_b.exists():
                snapshot_b_path = str(snapshot_file_b)
        
        # Perform diff
        diff_result = memory_differ.diff_snapshots(
            snapshot_a_path,
            snapshot_b_path,
            snapshot_a_id=request.snapshot_a_id or request.snapshot_a,
            snapshot_b_id=request.snapshot_b_id or request.snapshot_b
        )
        
        return DiffResponse(
            diff_id=diff_result['diff_id'],
            statistics=diff_result['statistics'],
            changed_pages=diff_result['changed_pages'],
            added_pages=diff_result['added_pages'],
            removed_pages=diff_result['removed_pages']
        )
    
    except Exception as e:
        logger.error(f"Error performing memory diff: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Diff failed: {str(e)}")

@router.post("/dna/extract", response_model=DNAExtractResponse)
async def extract_dna(request: DNAExtractRequest):
    """
    Extract DNA signature from artifact and classify.
    
    Args:
        request: DNA extraction request
        
    Returns:
        DNA signature, classification, and SHAP values
    """
    try:
        # Resolve artifact path
        artifact_path = request.artifact_path
        if not artifact_path:
            # Try to get from artifact store
            artifact_dir = artifact_store.get_artifact_dir(request.artifact_id)
            artifact_file = artifact_dir / "artifact.bin"
            if artifact_file.exists():
                artifact_path = str(artifact_file)
            else:
                raise HTTPException(status_code=404, detail=f"Artifact not found: {request.artifact_id}")
        
        if not Path(artifact_path).exists():
            raise HTTPException(status_code=404, detail=f"Artifact path not found: {artifact_path}")
        
        # Extract DNA
        logger.info(f"Extracting DNA from {artifact_path}")
        dna_data = dna_extractor.extract_dna(artifact_path, request.artifact_type)
        
        # Scan with YARA
        yara_matches = yara_wrapper.scan_file(artifact_path)
        dna_data['yara_matches'] = yara_matches
        
        # Serialize DNA
        dna_hash = dna_serializer.compute_dna_hash(dna_data)
        dna_id = str(uuid.uuid4())
        
        # Classify
        classification = classifier.predict(dna_data, return_shap=True)
        
        # Generate fingerprint
        fingerprint = fingerprinter.generate_fingerprint(dna_data, method='lsh')
        
        # Store DNA in database (would integrate with DB Core)
        # For now, just return results
        
        return DNAExtractResponse(
            dna_id=dna_id,
            dna_hash=dna_hash,
            dna_data=dna_data,
            classification=classification,
            yara_matches=yara_matches,
            fingerprint=fingerprint
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting DNA: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"DNA extraction failed: {str(e)}")

@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """
    Submit operator feedback for model improvement (Autolearn).
    
    Args:
        request: Feedback request with correct label
        
    Returns:
        Feedback confirmation and update status
    """
    try:
        # Initialize incremental trainer
        model_path = os.environ.get('MODEL_DIR', '/home/ransomeye/rebuild/ransomeye_forensic/ml/models')
        trainer = IncrementalTrainer(model_path=model_path)
        
        # Record feedback
        feedback_id = trainer.record_feedback(
            dna_id=request.dna_id,
            dna_data=request.dna_data,
            predicted_label=request.predicted_label,
            operator_label=request.operator_label,
            operator_notes=request.operator_notes
        )
        
        # Check if update should be triggered
        update_result = trainer.incremental_update(min_feedback_count=10)
        update_triggered = update_result is not None and update_result.get('update_method') != 'retrain_required'
        
        return FeedbackResponse(
            feedback_id=feedback_id,
            status="recorded",
            update_triggered=update_triggered
        )
    
    except Exception as e:
        logger.error(f"Error recording feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Feedback submission failed: {str(e)}")

@router.get("/dna/{dna_id}")
async def get_dna(dna_id: str):
    """
    Retrieve stored DNA signature by ID.
    
    Args:
        dna_id: DNA signature ID
        
    Returns:
        DNA signature data
    """
    # In production, would query database
    # For now, return placeholder
    raise HTTPException(status_code=501, detail="DNA retrieval not yet implemented")

@router.get("/diff/{diff_id}")
async def get_diff(diff_id: str):
    """
    Retrieve stored diff results by ID.
    
    Args:
        diff_id: Diff ID
        
    Returns:
        Diff results
    """
    # In production, would query database
    # For now, return placeholder
    raise HTTPException(status_code=501, detail="Diff retrieval not yet implemented")

