# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/context/context_injector.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Retrieves context, re-ranks, and injects into prompt

import os
from typing import List, Dict, Optional
import logging

from .retriever import HybridRetriever, RetrievalResult
from .embedder import LocalEmbedder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContextInjector:
    """
    Orchestrates context retrieval, re-ranking, and injection into prompts.
    """
    
    def __init__(
        self,
        embedder: Optional[LocalEmbedder] = None,
        retriever: Optional[HybridRetriever] = None,
        reranker: Optional[object] = None  # Will be ReRankerModel
    ):
        """
        Initialize context injector.
        
        Args:
            embedder: Embedder instance
            retriever: Retriever instance
            reranker: Optional re-ranker model
        """
        self.embedder = embedder or LocalEmbedder()
        self.retriever = retriever or HybridRetriever(embedding_dim=self.embedder.get_embedding_dim())
        self.reranker = reranker
    
    def inject_context(
        self,
        query: str,
        top_k: int = 5,
        max_context_length: int = 2000,
        use_reranker: bool = True
    ) -> Dict:
        """
        Retrieve and inject context for a query.
        
        Args:
            query: Query text
            top_k: Number of chunks to retrieve
            max_context_length: Maximum total context length in characters
            use_reranker: Whether to use re-ranker
            
        Returns:
            Dictionary with context and metadata
        """
        # Embed query
        query_embedding = self.embedder.encode(query)[0]
        
        # Retrieve chunks
        retrieval_results = self.retriever.retrieve(
            query=query,
            query_embedding=query_embedding,
            top_k=top_k * 2  # Retrieve more for re-ranking
        )
        
        # Re-rank if available
        if use_reranker and self.reranker and retrieval_results:
            retrieval_results = self._rerank(query, retrieval_results)
        
        # Select top chunks within length limit
        selected_chunks = self._select_chunks(retrieval_results, max_context_length)
        
        # Format context
        context_text = self._format_context(selected_chunks)
        
        return {
            'context': context_text,
            'chunks': [
                {
                    'chunk_id': r.chunk_id,
                    'text': r.text[:200],  # Preview
                    'score': r.score,
                    'source': r.source
                }
                for r in selected_chunks
            ],
            'num_chunks': len(selected_chunks),
            'total_length': len(context_text)
        }
    
    def _rerank(self, query: str, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """
        Re-rank retrieval results using re-ranker model.
        
        Args:
            query: Query text
            results: Initial retrieval results
            
        Returns:
            Re-ranked results
        """
        if not self.reranker:
            return results
        
        try:
            # Prepare pairs for re-ranking
            pairs = [(query, r.text) for r in results]
            
            # Get re-ranking scores
            rerank_scores = self.reranker.predict(pairs)
            
            # Update scores
            for i, result in enumerate(results):
                if i < len(rerank_scores):
                    # Combine original score with re-rank score
                    result.score = 0.5 * result.score + 0.5 * rerank_scores[i]
            
            # Re-sort by new scores
            results.sort(key=lambda x: x.score, reverse=True)
            
            logger.info(f"Re-ranked {len(results)} results")
        
        except Exception as e:
            logger.error(f"Error in re-ranking: {e}")
        
        return results
    
    def _select_chunks(
        self,
        results: List[RetrievalResult],
        max_length: int
    ) -> List[RetrievalResult]:
        """
        Select chunks within length limit.
        
        Args:
            results: Retrieval results
            max_length: Maximum total length
            
        Returns:
            Selected chunks
        """
        selected = []
        current_length = 0
        
        for result in results:
            chunk_length = len(result.text)
            if current_length + chunk_length <= max_length:
                selected.append(result)
                current_length += chunk_length
            else:
                break
        
        return selected
    
    def _format_context(self, chunks: List[RetrievalResult]) -> str:
        """
        Format chunks into context text.
        
        Args:
            chunks: Selected chunks
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"[Context {i}]\n{chunk.text}\n")
        
        return "\n".join(context_parts)
    
    def build_index(self, documents: List[Dict], embeddings: List[List[float]] = None):
        """
        Build retrieval index from documents.
        
        Args:
            documents: List of document dicts with 'text' and 'metadata'
            embeddings: Optional pre-computed embeddings
        """
        # Prepare chunks
        chunks = []
        for doc in documents:
            chunks.append({
                'chunk_id': doc.get('id', f"doc_{len(chunks)}"),
                'text': doc.get('text', ''),
                'metadata': doc.get('metadata', {})
            })
        
        # Compute embeddings if not provided
        if embeddings is None:
            texts = [chunk['text'] for chunk in chunks]
            embeddings = self.embedder.encode(texts)
        
        # Add to retriever
        self.retriever.add_chunks(chunks, embeddings)
        logger.info(f"Built index with {len(chunks)} chunks")

