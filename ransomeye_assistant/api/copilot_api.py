# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant/api/copilot_api.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: FastAPI application for SOC Copilot on port 8008

import os
import sys
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..retriever.ingestion_engine import IngestionEngine
from ..retriever.embedder import Embedder
from ..retriever.vector_store import VectorStore
from ..retriever.ranker_model import RankerModel
from ..llm.local_runner import LocalLLMRunner
from ..llm.prompt_builder import PromptBuilder
from ..feedback.feedback_collector import FeedbackCollector
from ..storage.kv_store import KVStore
from ..metrics.exporter import setup_metrics_endpoint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
ingestion_engine = IngestionEngine()
embedder = Embedder()
vector_store = VectorStore()
ranker = RankerModel()
llm_runner = LocalLLMRunner()
prompt_builder = PromptBuilder()
feedback_collector = FeedbackCollector()
kv_store = KVStore()

# Create FastAPI app
app = FastAPI(
    title="RansomEye SOC Copilot API",
    description="Offline RAG-based assistant for SOC operations",
    version="1.0.0"
)

# Setup metrics endpoint
setup_metrics_endpoint(app)

# Request/Response models
class AskRequest(BaseModel):
    """Ask question request model."""
    question: str
    top_k: int = 5
    include_shap: bool = True

class AskResponse(BaseModel):
    """Ask question response model."""
    answer: str
    sources: List[Dict[str, Any]]
    shap_explanations: Optional[Dict[str, Any]] = None

class FeedbackRequest(BaseModel):
    """Feedback request model."""
    query_id: str
    rating: str  # thumbs_up, thumbs_down, correction
    correction: Optional[str] = None
    comment: Optional[str] = None

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RansomEye SOC Copilot API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "embedding_model_available": embedder.is_model_available(),
        "llm_model_available": llm_runner.is_model_available(),
        "vector_store_ready": vector_store.is_index_loaded()
    }

@app.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    """
    Ingest a document (PDF/Log) -> Chunk -> Embed -> Index.
    
    Args:
        file: Document file to ingest
        
    Returns:
        Ingestion result
    """
    try:
        # Save uploaded file temporarily
        temp_path = Path(f"/tmp/ingest_{file.filename}")
        with open(temp_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        # Process document
        doc_id = str(uuid.uuid4())
        
        # Chunk document
        chunks = ingestion_engine.process_document(temp_path, doc_id)
        
        # Embed chunks
        embeddings = []
        chunk_ids = []
        for chunk in chunks:
            embedding = embedder.embed(chunk['text'])
            embeddings.append(embedding)
            chunk_id = f"{doc_id}_{chunk['chunk_index']}"
            chunk_ids.append(chunk_id)
            
            # Store chunk text in KV store
            kv_store.store(chunk_id, {
                'text': chunk['text'],
                'doc_id': doc_id,
                'chunk_index': chunk['chunk_index'],
                'metadata': chunk.get('metadata', {})
            })
        
        # Add to vector store
        vector_store.add_vectors(chunk_ids, embeddings)
        
        # Save index
        vector_store.save_index()
        
        # Cleanup temp file
        temp_path.unlink()
        
        logger.info(f"Ingested document: {doc_id} ({len(chunks)} chunks)")
        
        return {
            "doc_id": doc_id,
            "chunks_ingested": len(chunks),
            "status": "ingested"
        }
        
    except Exception as e:
        logger.error(f"Error ingesting document: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Ask a question -> Retrieve -> Rank -> Generate Answer.
    
    Args:
        request: Ask request with question
        
    Returns:
        Answer with sources and SHAP explanations
    """
    try:
        query_id = str(uuid.uuid4())
        
        # Embed query
        query_embedding = embedder.embed(request.question)
        
        # Retrieve candidates (top_k * 2 for re-ranking)
        candidate_k = request.top_k * 2
        candidate_ids, candidate_distances = vector_store.search(query_embedding, k=candidate_k)
        
        # Retrieve document texts
        candidates = []
        for chunk_id, distance in zip(candidate_ids, candidate_distances):
            doc_data = kv_store.get(chunk_id)
            if doc_data:
                candidates.append({
                    'chunk_id': chunk_id,
                    'text': doc_data['text'],
                    'distance': float(distance),
                    'metadata': doc_data.get('metadata', {})
                })
        
        # Re-rank candidates
        ranked_results = ranker.rank(request.question, candidates, top_k=request.top_k)
        
        # Extract top documents
        top_docs = [r['document'] for r in ranked_results]
        
        # Build RAG prompt
        prompt = prompt_builder.build_rag_prompt(request.question, top_docs)
        
        # Generate answer with LLM
        llm_response = llm_runner.generate(prompt)
        answer = llm_response.get('text', 'Unable to generate answer.')
        
        # Prepare sources
        sources = []
        for doc in top_docs:
            sources.append({
                'chunk_id': doc['chunk_id'],
                'text': doc['text'][:200] + '...' if len(doc['text']) > 200 else doc['text'],
                'metadata': doc.get('metadata', {})
            })
        
        # SHAP explanations if requested
        shap_explanations = None
        if request.include_shap and ranked_results:
            shap_explanations = ranker.get_shap_explanations(request.question, top_docs[0])
        
        # Log query for feedback
        feedback_collector.log_query(query_id, request.question, answer, sources, ranked_results)
        
        return AskResponse(
            answer=answer,
            sources=sources,
            shap_explanations=shap_explanations
        )
        
    except Exception as e:
        logger.error(f"Error processing question: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    Save user feedback (thumbs up/down/correction).
    
    Args:
        request: Feedback request
        
    Returns:
        Feedback submission result
    """
    try:
        feedback_collector.submit_feedback(
            query_id=request.query_id,
            rating=request.rating,
            correction=request.correction,
            comment=request.comment
        )
        
        return {
            "query_id": request.query_id,
            "status": "feedback_recorded"
        }
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.get("/stats")
async def get_stats():
    """Get statistics about the vector store."""
    stats = vector_store.get_stats()
    return stats

if __name__ == "__main__":
    import uvicorn
    
    host = os.environ.get('ASSISTANT_API_HOST', '0.0.0.0')
    port = int(os.environ.get('ASSISTANT_API_PORT', 8008))
    
    uvicorn.run(app, host=host, port=port)

