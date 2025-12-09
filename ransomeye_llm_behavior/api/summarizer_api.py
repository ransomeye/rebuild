# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/api/summarizer_api.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: FastAPI endpoints for behavioral analysis on port 8007

import os
import sys
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..context.context_injector import ContextInjector
from ..context.embedder import LocalEmbedder
from ..context.retriever import HybridRetriever
from ..security.security_filter import SecurityFilter
from ..llm_core.llm_runner import LLMRunner
from ..llm_core.confidence_estimator import ConfidenceEstimator
from ..llm_core.response_postproc import ResponsePostprocessor
from ..storage.summary_store import SummaryStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
embedder = LocalEmbedder()
retriever = HybridRetriever(embedding_dim=embedder.get_embedding_dim())
context_injector = ContextInjector(embedder=embedder, retriever=retriever)
security_filter = SecurityFilter()
llm_runner = LLMRunner()
confidence_estimator = ConfidenceEstimator()
postprocessor = ResponsePostprocessor()
summary_store = SummaryStore()

# Create FastAPI app
app = FastAPI(
    title="RansomEye LLM Behavior Summarizer API",
    description="Advanced LLM behavior analysis with security filters and regression testing",
    version="1.0.0"
)

# Request/Response models
class AnalyzeRequest(BaseModel):
    """Behavioral analysis request."""
    query: str
    context: Optional[Dict] = None
    deterministic: bool = False

class AnalyzeResponse(BaseModel):
    """Behavioral analysis response."""
    summary_id: str
    summary: str
    confidence_score: float
    security_filtered: bool
    shap_values: Optional[Dict] = None

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RansomEye LLM Behavior Summarizer API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "llm_available": llm_runner.is_available()
    }

@app.post("/behavior/analyze", response_model=AnalyzeResponse)
async def analyze_behavior(request: AnalyzeRequest):
    """
    Analyze behavior and generate summary.
    
    Args:
        request: Analysis request
        
    Returns:
        Analysis results with summary and confidence
    """
    try:
        # Security filter (pre-processing)
        input_allowed, filtered_input, violations = security_filter.filter_input(request.query)
        if not input_allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Input blocked by security policy: {len(violations)} violations"
            )
        
        # Inject context
        context_result = context_injector.inject_context(
            query=request.query,
            top_k=5,
            max_context_length=2000
        )
        
        # Build prompt
        prompt = f"Context:\n{context_result.get('context', '')}\n\nQuery: {request.query}\n\nSummary:"
        
        # Run LLM
        llm_result = llm_runner.generate(
            prompt=prompt,
            max_tokens=512,
            deterministic=request.deterministic,
            seed=42 if request.deterministic else None
        )
        
        output = llm_result.get('text', '')
        
        # Post-process
        processed = postprocessor.process(output, expected_format='text')
        processed_text = processed['text']
        
        # Security filter (post-processing)
        sanitized_output, redactions = security_filter.filter_output(processed_text)
        
        # Estimate confidence
        confidence_result = confidence_estimator.estimate(
            prompt=prompt,
            output=sanitized_output,
            context=context_result,
            return_shap=True
        )
        
        # Store summary
        summary_id = str(uuid.uuid4())
        summary_store.save_summary(
            summary_id=summary_id,
            query=request.query,
            summary=sanitized_output,
            confidence=confidence_result['confidence_score'],
            metadata={
                'deterministic': request.deterministic,
                'redactions': len(redactions)
            }
        )
        
        return AnalyzeResponse(
            summary_id=summary_id,
            summary=sanitized_output,
            confidence_score=confidence_result['confidence_score'],
            security_filtered=len(redactions) > 0,
            shap_values=confidence_result.get('shap_values')
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in behavioral analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    host = os.environ.get('LLM_API_HOST', '0.0.0.0')
    port = int(os.environ.get('LLM_PORT', 8007))
    
    uvicorn.run(app, host=host, port=port)

