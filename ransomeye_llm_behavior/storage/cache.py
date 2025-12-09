# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/storage/cache.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Semantic caching using vector similarity to serve cached answers

import os
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import logging

from ..context.embedder import LocalEmbedder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SemanticCache:
    """
    Semantic cache using vector similarity.
    Serves cached answers for similar queries.
    """
    
    def __init__(
        self,
        embedder: Optional[LocalEmbedder] = None,
        similarity_threshold: float = 0.85,
        max_cache_size: int = 1000
    ):
        """
        Initialize semantic cache.
        
        Args:
            embedder: Embedder instance
            similarity_threshold: Minimum similarity for cache hit
            max_cache_size: Maximum cache entries
        """
        self.embedder = embedder or LocalEmbedder()
        self.similarity_threshold = similarity_threshold
        self.max_cache_size = max_cache_size
        
        self.cache: List[Dict] = []
    
    def get(self, query: str) -> Optional[Dict]:
        """
        Get cached result for query.
        
        Args:
            query: Query text
            
        Returns:
            Cached result or None
        """
        if not self.cache:
            return None
        
        # Embed query
        query_embedding = self.embedder.encode(query)[0]
        
        # Find most similar cached query
        best_match = None
        best_similarity = 0.0
        
        for entry in self.cache:
            cached_embedding = entry.get('embedding')
            if cached_embedding:
                similarity = self._cosine_similarity(query_embedding, cached_embedding)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = entry
        
        if best_match and best_similarity >= self.similarity_threshold:
            logger.info(f"Cache hit: similarity={best_similarity:.3f}")
            return best_match.get('result')
        
        return None
    
    def put(self, query: str, result: Dict):
        """
        Store result in cache.
        
        Args:
            query: Query text
            result: Result dictionary
        """
        # Embed query
        query_embedding = self.embedder.encode(query)[0]
        
        # Add to cache
        cache_entry = {
            'query': query,
            'embedding': query_embedding,
            'result': result,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.cache.append(cache_entry)
        
        # Limit cache size
        if len(self.cache) > self.max_cache_size:
            # Remove oldest entries
            self.cache = self.cache[-self.max_cache_size:]
        
        logger.info(f"Cached result for query (cache size: {len(self.cache)})")
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)

