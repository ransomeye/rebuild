# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/context/retriever.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Hybrid search wrapper combining vector (FAISS) and sparse (BM25) retrieval

import os
from typing import List, Dict, Tuple
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import FAISS
try:
    import faiss
    import numpy as np
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("faiss-cpu not available. Vector search will be limited.")

# Try to import BM25
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    logger.warning("rank-bm25 not available. Sparse search will be limited.")


@dataclass
class RetrievalResult:
    """Represents a retrieval result."""
    chunk_id: str
    text: str
    score: float
    source: str  # 'vector' or 'sparse' or 'hybrid'
    metadata: Dict = None


class HybridRetriever:
    """
    Hybrid retriever combining vector (FAISS) and sparse (BM25) search.
    """
    
    def __init__(
        self,
        embedding_dim: int = 384,
        index_path: str = None,
        use_vector: bool = True,
        use_sparse: bool = True,
        vector_weight: float = 0.6
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            embedding_dim: Dimension of embeddings
            index_path: Path to FAISS index file
            use_vector: Whether to use vector search
            use_sparse: Whether to use sparse (BM25) search
            vector_weight: Weight for vector scores in hybrid (0-1)
        """
        self.embedding_dim = embedding_dim
        self.use_vector = use_vector and FAISS_AVAILABLE
        self.use_sparse = use_sparse and BM25_AVAILABLE
        self.vector_weight = vector_weight
        
        # Vector store (FAISS)
        self.index = None
        self.chunks = []  # List of (chunk_id, text, metadata)
        self.embeddings = None
        
        # Sparse store (BM25)
        self.bm25 = None
        self.tokenized_chunks = []
        
        if index_path and os.path.exists(index_path):
            self.load_index(index_path)
    
    def add_chunks(self, chunks: List[Dict], embeddings: List[List[float]] = None):
        """
        Add chunks to the retriever.
        
        Args:
            chunks: List of dicts with 'chunk_id', 'text', 'metadata'
            embeddings: Optional pre-computed embeddings
        """
        self.chunks = chunks
        
        # Build vector index
        if self.use_vector and embeddings:
            self.embeddings = np.array(embeddings, dtype=np.float32)
            self._build_faiss_index()
        
        # Build BM25 index
        if self.use_sparse:
            self._build_bm25_index()
    
    def _build_faiss_index(self):
        """Build FAISS index for vector search."""
        if not FAISS_AVAILABLE or self.embeddings is None:
            return
        
        try:
            # Create index
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            self.index.add(self.embeddings)
            logger.info(f"Built FAISS index with {len(self.chunks)} chunks")
        except Exception as e:
            logger.error(f"Error building FAISS index: {e}")
            self.use_vector = False
    
    def _build_bm25_index(self):
        """Build BM25 index for sparse search."""
        if not BM25_AVAILABLE:
            return
        
        try:
            # Tokenize chunks
            self.tokenized_chunks = []
            for chunk in self.chunks:
                text = chunk.get('text', '')
                tokens = text.lower().split()
                self.tokenized_chunks.append(tokens)
            
            if self.tokenized_chunks:
                self.bm25 = BM25Okapi(self.tokenized_chunks)
                logger.info(f"Built BM25 index with {len(self.chunks)} chunks")
        except Exception as e:
            logger.error(f"Error building BM25 index: {e}")
            self.use_sparse = False
    
    def retrieve(
        self,
        query: str,
        query_embedding: List[float] = None,
        top_k: int = 10,
        use_hybrid: bool = True
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant chunks for query.
        
        Args:
            query: Query text
            query_embedding: Optional pre-computed query embedding
            top_k: Number of results to return
            use_hybrid: Whether to combine vector and sparse results
            
        Returns:
            List of RetrievalResult objects
        """
        results = []
        
        # Vector search
        vector_results = []
        if self.use_vector and query_embedding:
            vector_results = self._vector_search(query_embedding, top_k)
        
        # Sparse search
        sparse_results = []
        if self.use_sparse:
            sparse_results = self._sparse_search(query, top_k)
        
        # Combine results
        if use_hybrid and vector_results and sparse_results:
            results = self._merge_results(vector_results, sparse_results, top_k)
        elif vector_results:
            results = vector_results
        elif sparse_results:
            results = sparse_results
        else:
            # Fallback: return first chunks
            results = [
                RetrievalResult(
                    chunk_id=chunk.get('chunk_id', ''),
                    text=chunk.get('text', ''),
                    score=1.0 - (i / len(self.chunks)),
                    source='fallback',
                    metadata=chunk.get('metadata', {})
                )
                for i, chunk in enumerate(self.chunks[:top_k])
            ]
        
        return results[:top_k]
    
    def _vector_search(self, query_embedding: List[float], top_k: int) -> List[RetrievalResult]:
        """Perform vector search using FAISS."""
        if not self.index or not FAISS_AVAILABLE:
            return []
        
        try:
            query_vec = np.array([query_embedding], dtype=np.float32)
            distances, indices = self.index.search(query_vec, min(top_k, len(self.chunks)))
            
            results = []
            for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < len(self.chunks):
                    chunk = self.chunks[idx]
                    # Convert distance to similarity score (lower distance = higher score)
                    score = 1.0 / (1.0 + dist)
                    results.append(RetrievalResult(
                        chunk_id=chunk.get('chunk_id', ''),
                        text=chunk.get('text', ''),
                        score=score,
                        source='vector',
                        metadata=chunk.get('metadata', {})
                    ))
            
            return results
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return []
    
    def _sparse_search(self, query: str, top_k: int) -> List[RetrievalResult]:
        """Perform sparse search using BM25."""
        if not self.bm25 or not BM25_AVAILABLE:
            return []
        
        try:
            query_tokens = query.lower().split()
            scores = self.bm25.get_scores(query_tokens)
            
            # Get top-k indices
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
            
            results = []
            max_score = max(scores) if scores else 1.0
            for idx in top_indices:
                if scores[idx] > 0:
                    chunk = self.chunks[idx]
                    # Normalize score
                    score = scores[idx] / max_score if max_score > 0 else 0.0
                    results.append(RetrievalResult(
                        chunk_id=chunk.get('chunk_id', ''),
                        text=chunk.get('text', ''),
                        score=score,
                        source='sparse',
                        metadata=chunk.get('metadata', {})
                    ))
            
            return results
        except Exception as e:
            logger.error(f"Error in sparse search: {e}")
            return []
    
    def _merge_results(
        self,
        vector_results: List[RetrievalResult],
        sparse_results: List[RetrievalResult],
        top_k: int
    ) -> List[RetrievalResult]:
        """Merge vector and sparse results using weighted combination."""
        # Create score maps
        vector_scores = {r.chunk_id: r.score for r in vector_results}
        sparse_scores = {r.chunk_id: r.score for r in sparse_results}
        
        # Combine chunk IDs
        all_chunk_ids = set(vector_scores.keys()) | set(sparse_scores.keys())
        
        # Compute hybrid scores
        hybrid_results = []
        for chunk_id in all_chunk_ids:
            vector_score = vector_scores.get(chunk_id, 0.0)
            sparse_score = sparse_scores.get(chunk_id, 0.0)
            
            hybrid_score = (self.vector_weight * vector_score) + ((1 - self.vector_weight) * sparse_score)
            
            # Find chunk text
            chunk_text = ''
            metadata = {}
            for chunk in self.chunks:
                if chunk.get('chunk_id') == chunk_id:
                    chunk_text = chunk.get('text', '')
                    metadata = chunk.get('metadata', {})
                    break
            
            hybrid_results.append(RetrievalResult(
                chunk_id=chunk_id,
                text=chunk_text,
                score=hybrid_score,
                source='hybrid',
                metadata=metadata
            ))
        
        # Sort by score and return top-k
        hybrid_results.sort(key=lambda x: x.score, reverse=True)
        return hybrid_results[:top_k]
    
    def save_index(self, index_path: str):
        """Save FAISS index to file."""
        if self.index and FAISS_AVAILABLE:
            try:
                faiss.write_index(self.index, index_path)
                logger.info(f"Saved FAISS index to {index_path}")
            except Exception as e:
                logger.error(f"Error saving index: {e}")
    
    def load_index(self, index_path: str):
        """Load FAISS index from file."""
        if FAISS_AVAILABLE and os.path.exists(index_path):
            try:
                self.index = faiss.read_index(index_path)
                logger.info(f"Loaded FAISS index from {index_path}")
            except Exception as e:
                logger.error(f"Error loading index: {e}")

