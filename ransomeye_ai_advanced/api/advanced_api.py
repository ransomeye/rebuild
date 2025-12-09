# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/api/advanced_api.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: FastAPI endpoints for Phase 17 AI Multi-Agent Governor (POST /agent/chat)

import os
import sys
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..multi_agent.orchestrator import MultiAgentOrchestrator
from ..governor.llm_governor import LLMGovernor
from ..storage.conversation_store import ConversationStore
from ..storage.summary_store import SummaryStore
from .auth_middleware import verify_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
orchestrator = MultiAgentOrchestrator()
governor = LLMGovernor()
conversation_store = ConversationStore()
summary_store = SummaryStore()

# Create FastAPI app
app = FastAPI(
    title="RansomEye Phase 17: AI Multi-Agent Governor API",
    description="Advanced AI Assistant with multi-agent orchestration and governance",
    version="1.0.0"
)

# Request/Response models
class ChatRequest(BaseModel):
    """Chat request model."""
    query: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    include_shap: bool = True

class ChatResponse(BaseModel):
    """Chat response model."""
    conversation_id: str
    query: str
    answer: str
    verification: Dict[str, Any]
    metadata: Dict[str, Any]

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RansomEye Phase 17: AI Multi-Agent Governor",
        "version": "1.0.0",
        "status": "operational",
        "capabilities": ["Multi-Agent Orchestration", "LLM Governance", "Rate Limiting", "Hallucination Detection"]
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "orchestrator": orchestrator is not None,
        "governor": governor is not None
    }

@app.post("/agent/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_id: str = Depends(verify_token)
):
    """
    Process chat query through multi-agent pipeline.
    
    Args:
        request: Chat request
        user_id: Authenticated user ID
        
    Returns:
        Chat response with answer and metadata
    """
    try:
        # Step 1: Governor check (rate limit + policy)
        request_allowed, error_msg, request_metadata = await governor.check_request(
            input_text=request.query,
            user_id=user_id or request.user_id,
            tokens=1
        )
        
        if not request_allowed:
            raise HTTPException(status_code=429, detail=error_msg)
        
        # Step 2: Process through orchestrator
        result = await orchestrator.process_query(
            query=request.query,
            conversation_id=request.conversation_id,
            user_id=user_id or request.user_id
        )
        
        # Step 3: Validate output
        context = ' '.join([
            str(item.get('text', '')) if isinstance(item, dict) else str(item)
            for item in result.get('metadata', {}).get('intermediate_results', {}).get('retriever_output', [])
        ])
        
        output_valid, validation_result = governor.validate_output(
            output_text=result.get('answer', ''),
            context=context,
            user_id=user_id or request.user_id
        )
        
        if not output_valid:
            logger.warning(f"Output validation failed: {validation_result}")
            # Still return answer but with warning
        
        # Step 4: Store conversation
        conversation_store.save_conversation(
            conversation_id=result['conversation_id'],
            user_id=user_id or request.user_id,
            query=request.query,
            answer=result.get('answer', ''),
            agent_trace=result.get('metadata', {}),
            intermediate_results=result.get('intermediate_results', {}),
            verification=validation_result,
            metadata=result.get('metadata', {})
        )
        
        # Step 5: Store summary
        summary_store.save_summary(
            conversation_id=result['conversation_id'],
            query=request.query,
            answer=result.get('answer', ''),
            shap_explanations=None,  # Would be populated by SHAP integration
            verification=validation_result,
            model_version=os.environ.get('MODEL_VERSION', '1.0.0')
        )
        
        # Step 6: Return response
        return ChatResponse(
            conversation_id=result['conversation_id'],
            query=request.query,
            answer=result.get('answer', ''),
            verification=validation_result,
            metadata={
                **result.get('metadata', {}),
                'validation': validation_result,
                'request_metadata': request_metadata
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversation/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user_id: str = Depends(verify_token)
):
    """Get conversation by ID."""
    conversation = conversation_store.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation

@app.get("/stats")
async def get_stats(user_id: str = Depends(verify_token)):
    """Get orchestrator and governor statistics."""
    return {
        'orchestrator': orchestrator.get_stats(),
        'governor': governor.get_stats()
    }

if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('ASSISTANT_API_PORT', 8008))
    uvicorn.run(app, host='0.0.0.0', port=port)

