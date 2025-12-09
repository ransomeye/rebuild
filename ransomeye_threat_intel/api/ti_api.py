# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/api/ti_api.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: FastAPI on Port 8013 with POST /ingest, GET /ioc/{value}, POST /export/bundle

import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..normalizer.normalizer import IOCNormalizer
from ..normalizer.enrichment import IOCEnricher
from ..dedup.fingerprint import IOCFingerprint
from ..dedup.deduper import IOCDeduplicator
from ..trust.trust_score import TrustScorer
from ..storage.ti_store import TIStore
from ..storage.provenance_store import ProvenanceStore
from ..tools.export_bundle import export_bundle as export_bundle_tool
from .auth_middleware import verify_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
normalizer = IOCNormalizer()
enricher = IOCEnricher()
deduper = IOCDeduplicator()
trust_scorer = TrustScorer()
ti_store = TIStore()
provenance_store = ProvenanceStore()

# Set deduper's db_store
deduper.db_store = ti_store

# Create FastAPI app
app = FastAPI(
    title="RansomEye Threat Intel API",
    description="Threat Intelligence Feed Engine API",
    version="1.0.0"
)

# Request/Response models
class IngestRequest(BaseModel):
    """Ingest IOC request."""
    iocs: List[Dict[str, Any]]

class IOCResponse(BaseModel):
    """IOC response."""
    value: str
    type: str
    trust_score: float
    shap_explanation: Optional[Dict[str, Any]]
    campaign_id: Optional[int]

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RansomEye Threat Intel API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.post("/ingest")
async def ingest(
    request: IngestRequest,
    user_id: str = Depends(verify_token)
):
    """Ingest raw IOCs."""
    ingested_count = 0
    
    for raw_ioc in request.iocs:
        try:
            # Normalize
            normalized = normalizer.normalize(raw_ioc)
            
            # Enrich
            enriched = enricher.enrich(normalized)
            
            # Generate fingerprint
            fingerprint = IOCFingerprint.generate(enriched)
            
            # Deduplicate
            is_duplicate, existing_id, match_info = deduper.deduplicate(enriched)
            
            if is_duplicate:
                # Update existing IOC
                ioc_id = existing_id
            else:
                # Calculate trust score
                trust_result = trust_scorer.score(
                    source_reputation=0.7,  # Default
                    age_days=0.0,
                    sightings_count=1
                )
                enriched['trust_score'] = trust_result['trust_score']
                
                # Save new IOC
                ioc_id = ti_store.save_ioc(enriched, fingerprint)
            
            # Record provenance
            provenance_store.record_provenance(
                ioc_id=ioc_id,
                fingerprint=fingerprint,
                source=enriched.get('source', 'api'),
                source_id=enriched.get('source_id'),
                metadata=match_info
            )
            
            ingested_count += 1
        except Exception as e:
            logger.error(f"Error ingesting IOC: {e}")
    
    return {"ingested": ingested_count, "total": len(request.iocs)}

@app.get("/ioc/{value}")
async def get_ioc(
    value: str,
    user_id: str = Depends(verify_token)
):
    """Get IOC by value with score, SHAP, and campaign."""
    # Find IOC
    # This is simplified - real implementation would search by value
    fingerprint = IOCFingerprint.generate_from_value('unknown', value)
    ioc = ti_store.get_ioc_by_fingerprint(fingerprint)
    
    if not ioc:
        raise HTTPException(status_code=404, detail="IOC not found")
    
    # Calculate trust score
    trust_result = trust_scorer.score(
        source_reputation=0.7,
        age_days=0.0,
        sightings_count=1
    )
    
    return IOCResponse(
        value=ioc['value'],
        type=ioc['type'],
        trust_score=trust_result['trust_score'],
        shap_explanation=trust_result.get('shap_explanation'),
        campaign_id=ioc.get('campaign_id')
    )

@app.post("/export/bundle")
async def export_bundle(
    filters: Optional[Dict[str, Any]] = None,
    user_id: str = Depends(verify_token)
):
    """Export IOC bundle as signed tarball."""
    try:
        from datetime import datetime
        import tempfile
        
        # Get IOCs from database based on filters
        # Simplified - real implementation would query DB with filters
        # For now, get all IOCs (would be filtered in production)
        iocs = []  # Would be populated from ti_store based on filters
        
        # Generate output path
        output_path = f"/tmp/ti_bundle_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.tar.gz"
        
        # Export bundle
        result = export_bundle_tool(
            iocs=iocs,
            output_path=output_path,
            sign=True
        )
        
        return {
            "status": "success",
            "bundle_path": output_path,
            "ioc_count": result.get('ioc_count', 0),
            "bundle_hash": result.get('bundle_hash'),
            "signed": result.get('signed', True)
        }
    except Exception as e:
        logger.error(f"Error exporting bundle: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('TI_API_PORT', 8013))
    uvicorn.run(app, host='0.0.0.0', port=port)

