# Path and File Name : /home/ransomeye/rebuild/ransomeye_hnmp_engine/api/hnmp_api.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: FastAPI application for HNMP Engine on port 8101

import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..engine.compliance_evaluator import ComplianceEvaluator
from ..engine.scorer import HealthScorer
from ..engine.inventory_manager import InventoryManager
from ..engine.remediation_suggester import RemediationSuggester
from ..rules.loader import RulesLoader
from ..storage.host_db import HostDB
from ..storage.history_store import HistoryStore
from ..metrics.exporter import setup_metrics_endpoint
from .auth_middleware import AuthMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
rules_loader = RulesLoader()
compliance_evaluator = ComplianceEvaluator(rules_loader)
health_scorer = HealthScorer(compliance_evaluator=compliance_evaluator)
inventory_manager = InventoryManager()
remediation_suggester = RemediationSuggester()
host_db = HostDB()
history_store = HistoryStore()

# Create FastAPI app
app = FastAPI(
    title="RansomEye HNMP Engine API",
    description="Host Network Management & Posture - Compliance and health scoring",
    version="1.0.0"
)

# Add auth middleware
app.add_middleware(AuthMiddleware, require_auth=os.environ.get('HNMP_REQUIRE_AUTH', 'true').lower() == 'true')

# Setup metrics endpoint
setup_metrics_endpoint(app)

# Request/Response models
class HostProfileRequest(BaseModel):
    """Host profile ingestion request."""
    host_id: Optional[str] = None
    profile: Dict[str, Any] = Field(..., description="Host profile JSON with OS, packages, sysctl, services, etc.")

class FeedbackRequest(BaseModel):
    """Analyst feedback request for autolearn."""
    host_id: str
    actual_risk_factor: float = Field(..., ge=0.0, le=1.0, description="Analyst-provided risk factor")
    notes: Optional[str] = None

class HealthScoreResponse(BaseModel):
    """Health score response."""
    host_id: str
    score: float
    base_score: float
    risk_factor: float
    risk_adjustment: float
    failed_counts: Dict[str, int]
    shap_explanation: Dict[str, Any]
    compliance_results: List[Dict[str, Any]]
    remediations: List[Dict[str, Any]]

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RansomEye HNMP Engine API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    try:
        # Check database connection
        hosts = host_db.list_hosts()
        return {
            "status": "healthy",
            "database_connected": True,
            "total_hosts": len(hosts),
            "policies_loaded": len(rules_loader.get_all_policies())
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.post("/ingest/profile")
async def ingest_profile(request: HostProfileRequest, background_tasks: BackgroundTasks):
    """
    Accept and process host profile.
    
    Args:
        request: Host profile request
        background_tasks: FastAPI background tasks
        
    Returns:
        Processing result with host_id
    """
    try:
        # Upsert host profile
        profile = request.profile.copy()
        if request.host_id:
            profile['host_id'] = request.host_id
        
        host_id = inventory_manager.upsert_host(profile)
        
        # Process profile in background (evaluate compliance, calculate score)
        background_tasks.add_task(_process_host_profile, host_id, profile)
        
        return {
            "host_id": host_id,
            "status": "accepted",
            "message": "Profile ingested successfully"
        }
        
    except Exception as e:
        logger.error(f"Error ingesting profile: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

def _process_host_profile(host_id: str, profile: Dict[str, Any]):
    """Process host profile in background: evaluate compliance and calculate score."""
    try:
        # Evaluate compliance
        compliance_results = compliance_evaluator.evaluate_all_rules(profile)
        
        # Save compliance results
        host_db.save_compliance_results(host_id, compliance_results)
        
        # Calculate health score
        host_data = {'profile': profile, 'host_id': host_id}
        score_result = health_scorer.calculate_health_score(host_data, compliance_results)
        
        # Save health score
        failed_counts = score_result['failed_counts']
        host_db.save_health_score(
            host_id=host_id,
            score=score_result['score'],
            base_score=score_result['base_score'],
            risk_factor=score_result['risk_factor'],
            failed_counts=failed_counts,
            shap_explanation=score_result['shap_explanation']
        )
        
        # Save daily snapshot
        inventory_manager.save_score_snapshot(host_id, score_result)
        
        logger.info(f"Processed profile for host: {host_id}, score: {score_result['score']:.2f}")
        
    except Exception as e:
        logger.error(f"Error processing profile for host {host_id}: {e}", exc_info=True)

@app.get("/health/score/{host_id}", response_model=HealthScoreResponse)
async def get_health_score(host_id: str):
    """
    Get health score with SHAP explanation for a host.
    
    Args:
        host_id: Host identifier
        
    Returns:
        Health score response with SHAP explanation
    """
    try:
        # Get host profile
        host = host_db.get_host(host_id)
        if not host:
            raise HTTPException(status_code=404, detail="Host not found")
        
        # Get latest compliance results
        compliance_results = host_db.get_compliance_results(host_id)
        
        # Calculate fresh score
        host_data = {'profile': host['profile'], 'host_id': host_id}
        score_result = health_scorer.calculate_health_score(host_data, compliance_results)
        
        # Get remediation suggestions
        rules = rules_loader.get_rules()
        remediations = remediation_suggester.get_remediations_for_failures(rules, compliance_results)
        remediations = remediation_suggester.prioritize_remediations(remediations)
        
        return HealthScoreResponse(
            host_id=host_id,
            score=score_result['score'],
            base_score=score_result['base_score'],
            risk_factor=score_result['risk_factor'],
            risk_adjustment=score_result['risk_adjustment'],
            failed_counts=score_result['failed_counts'],
            shap_explanation=score_result['shap_explanation'],
            compliance_results=compliance_results,
            remediations=remediations
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting health score: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    Submit analyst feedback for autolearn.
    
    Args:
        request: Feedback request with actual risk factor
        
    Returns:
        Feedback acceptance confirmation
    """
    try:
        # In production, would save to feedback table for incremental trainer
        # For now, log the feedback
        logger.info(f"Received feedback for host {request.host_id}: risk_factor={request.actual_risk_factor}, notes={request.notes}")
        
        # TODO: Store feedback in database for incremental training
        # feedback_db.save_feedback(request.host_id, request.actual_risk_factor, request.notes)
        
        return {
            "status": "accepted",
            "message": "Feedback recorded for autolearn",
            "host_id": request.host_id
        }
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.get("/hosts")
async def list_hosts():
    """
    List all hosts.
    
    Returns:
        List of hosts
    """
    try:
        hosts = inventory_manager.list_hosts()
        return {
            "hosts": hosts,
            "total": len(hosts)
        }
    except Exception as e:
        logger.error(f"Error listing hosts: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/hosts/{host_id}")
async def get_host(host_id: str):
    """Get host details."""
    try:
        host = inventory_manager.get_host(host_id)
        if not host:
            raise HTTPException(status_code=404, detail="Host not found")
        return host
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting host: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/hosts/{host_id}/history")
async def get_host_history(host_id: str, days: int = 30):
    """
    Get score history for a host.
    
    Args:
        host_id: Host identifier
        days: Number of days to retrieve
        
    Returns:
        Score history
    """
    try:
        history = inventory_manager.get_host_history(host_id, days)
        return {
            "host_id": host_id,
            "days": days,
            "history": history
        }
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/fleet/stats")
async def get_fleet_stats():
    """
    Get fleet-wide statistics.
    
    Returns:
        Fleet statistics
    """
    try:
        stats = host_db.get_fleet_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting fleet stats: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/fleet/trend")
async def get_fleet_trend(days: int = 30):
    """
    Get fleet-wide score trends.
    
    Args:
        days: Number of days to analyze
        
    Returns:
        Fleet trend data
    """
    try:
        trend = history_store.get_fleet_trend(days)
        return trend
    except Exception as e:
        logger.error(f"Error getting fleet trend: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/policies")
async def list_policies():
    """List loaded compliance policies."""
    try:
        policies = rules_loader.get_all_policies()
        return {
            "policies": {name: len(rules) for name, rules in policies.items()},
            "total_policies": len(policies),
            "total_rules": sum(len(rules) for rules in policies.values())
        }
    except Exception as e:
        logger.error(f"Error listing policies: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    host = os.environ.get('HNMP_API_HOST', '0.0.0.0')
    port = int(os.environ.get('HNMP_API_PORT', 8101))
    
    uvicorn.run(app, host=host, port=port)

