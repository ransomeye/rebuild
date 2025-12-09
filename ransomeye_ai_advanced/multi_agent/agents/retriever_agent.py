# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/multi_agent/agents/retriever_agent.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Retriever agent that wraps Phase 7's Vector Store for context retrieval

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from .base_agent import BaseAgent, AgentState
from ..message_bus import Message

# Try to import retriever from Phase 7/15
try:
    from ransomeye_llm_behavior.context.retriever import HybridRetriever, RetrievalResult
    RETRIEVER_AVAILABLE = True
except ImportError:
    try:
        from ransomeye_assistant.retriever.vector_store import VectorStore
        RETRIEVER_AVAILABLE = True
    except ImportError:
        RETRIEVER_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RetrieverAgent(BaseAgent):
    """
    Retriever agent that retrieves relevant context from knowledge base.
    Wraps Phase 7's Vector Store and hybrid retriever.
    """
    
    def __init__(
        self,
        agent_name: str,
        message_bus,
        retriever: Optional[Any] = None,
        top_k: int = 10
    ):
        """
        Initialize retriever agent.
        
        Args:
            agent_name: Agent name
            message_bus: Message bus instance
            retriever: Optional retriever instance
            top_k: Number of results to retrieve
        """
        super().__init__(
            agent_name=agent_name,
            message_bus=message_bus,
            description="Retrieves relevant context from knowledge base"
        )
        self.retriever = retriever
        self.top_k = top_k
        
        # Initialize retriever if not provided
        if not self.retriever and RETRIEVER_AVAILABLE:
            try:
                index_path = os.environ.get('VECTOR_INDEX_PATH')
                self.retriever = HybridRetriever(index_path=index_path)
            except Exception as e:
                logger.warning(f"Could not initialize retriever: {e}")
    
    async def process(
        self,
        message: Message,
        state: AgentState
    ) -> tuple[Optional[Message], AgentState]:
        """
        Process retrieval request.
        
        Args:
            message: Incoming message with query
            state: Current conversation state
            
        Returns:
            Tuple of (output_message, updated_state)
        """
        try:
            query = message.payload.get('query', state.user_query)
            top_k = message.payload.get('top_k', self.top_k)
            
            # Retrieve relevant context
            results = await self._retrieve(query, top_k)
            
            # Update state
            state.context['retrieved_context'] = results
            state.intermediate_results['retriever_output'] = results
            
            # Create response message
            response_message = Message(
                sender=self.agent_name,
                receiver="orchestrator",
                message_type="retrieval_result",
                payload={
                    'results': [
                        {
                            'chunk_id': r.chunk_id if hasattr(r, 'chunk_id') else r.get('chunk_id', ''),
                            'text': r.text if hasattr(r, 'text') else r.get('text', ''),
                            'score': r.score if hasattr(r, 'score') else r.get('score', 0.0),
                            'source': r.source if hasattr(r, 'source') else r.get('source', 'unknown'),
                            'metadata': r.metadata if hasattr(r, 'metadata') else r.get('metadata', {})
                        }
                        for r in results
                    ],
                    'query': query
                },
                correlation_id=message.correlation_id or message.message_id
            )
            
            logger.info(f"Retriever found {len(results)} results for query: {query[:50]}...")
            return response_message, state
            
        except Exception as e:
            logger.error(f"Error in retriever agent: {e}")
            state.metadata['retriever_error'] = str(e)
            # Return empty results on error
            state.context['retrieved_context'] = []
            return None, state
    
    async def _retrieve(self, query: str, top_k: int) -> List[Any]:
        """
        Retrieve relevant context.
        
        Args:
            query: Search query
            top_k: Number of results
            
        Returns:
            List of retrieval results
        """
        if not self.retriever:
            logger.warning("Retriever not available, returning empty results")
            return []
        
        try:
            # Try hybrid retriever first
            if isinstance(self.retriever, HybridRetriever):
                # For hybrid retriever, we need query embedding
                # For now, use text-only retrieval
                results = self.retriever.retrieve(
                    query=query,
                    top_k=top_k,
                    use_hybrid=True
                )
                return results
            else:
                # Fallback: try vector store
                if hasattr(self.retriever, 'search'):
                    results = self.retriever.search(query, top_k=top_k)
                    return results
                else:
                    logger.warning("Retriever does not support search method")
                    return []
                    
        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            return []

