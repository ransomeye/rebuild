# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant/retriever/vector_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Wrapper for FAISS vector store

import os
import shutil
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import FAISS
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("faiss-cpu not available, vector store will not work")

class VectorStore:
    """
    Manages FAISS vector store for document embeddings.
    """
    
    def __init__(self, index_path: str = None, dimension: int = 384):
        """
        Initialize vector store.
        
        Args:
            index_path: Path to FAISS index file
            dimension: Embedding dimension
        """
        self.dimension = dimension
        self.index_path = Path(index_path or os.environ.get(
            'FAISS_INDEX_PATH',
            os.path.join(os.environ.get('ASSISTANT_DATA_DIR', '/home/ransomeye/rebuild/ransomeye_assistant/data'), 'index.faiss')
        ))
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.index = None
        self.id_map = {}  # Map FAISS index position to chunk_id
        self.chunk_id_to_index = {}  # Reverse map
        
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        """Load existing index or create new one."""
        if not FAISS_AVAILABLE:
            logger.critical("FAISS not available, vector store disabled")
            return
        
        if self.index_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
                logger.info(f"Loaded FAISS index from: {self.index_path}")
                # Note: In production, would also load id_map from separate file
            except Exception as e:
                logger.warning(f"Failed to load index: {e}, creating new index")
                self._create_index()
        else:
            self._create_index()
    
    def _create_index(self):
        """Create new FAISS index."""
        if not FAISS_AVAILABLE:
            return
        
        # Create L2 distance index
        self.index = faiss.IndexFlatL2(self.dimension)
        logger.info(f"Created new FAISS index (dimension={self.dimension})")
    
    def is_index_loaded(self) -> bool:
        """
        Check if index is loaded.
        
        Returns:
            True if index is loaded, False otherwise
        """
        return self.index is not None and FAISS_AVAILABLE
    
    def add_vectors(self, chunk_ids: List[str], embeddings: List[np.ndarray]):
        """
        Add vectors to index.
        
        Args:
            chunk_ids: List of chunk identifiers
            embeddings: List of embedding vectors
        """
        if not self.is_index_loaded():
            raise RuntimeError("FAISS index not available")
        
        # Convert to numpy array
        vectors = np.array(embeddings).astype('float32')
        
        # Add to index
        start_idx = self.index.ntotal
        self.index.add(vectors)
        
        # Update id maps
        for i, chunk_id in enumerate(chunk_ids):
            idx = start_idx + i
            self.id_map[idx] = chunk_id
            self.chunk_id_to_index[chunk_id] = idx
        
        logger.info(f"Added {len(chunk_ids)} vectors to index")
    
    def search(self, query_embedding: np.ndarray, k: int = 5) -> Tuple[List[str], List[float]]:
        """
        Search for similar vectors.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            
        Returns:
            Tuple of (chunk_ids, distances)
        """
        if not self.is_index_loaded():
            raise RuntimeError("FAISS index not available")
        
        # Reshape query to 2D
        query = query_embedding.reshape(1, -1).astype('float32')
        
        # Search
        distances, indices = self.index.search(query, k)
        
        # Convert indices to chunk_ids
        chunk_ids = []
        result_distances = []
        
        for idx, dist in zip(indices[0], distances[0]):
            if idx < 0:  # FAISS returns -1 for invalid results
                continue
            chunk_id = self.id_map.get(idx)
            if chunk_id:
                chunk_ids.append(chunk_id)
                result_distances.append(float(dist))
        
        return chunk_ids, result_distances
    
    def save_index(self):
        """Save index to disk (atomic operation)."""
        if not self.is_index_loaded():
            return
        
        try:
            # Atomic write: save to temporary file first
            temp_path = Path(str(self.index_path) + '.tmp')
            faiss.write_index(self.index, str(temp_path))
            
            # Atomic swap: rename temp to final
            if self.index_path.exists():
                backup_path = Path(str(self.index_path) + '.backup')
                shutil.copy2(self.index_path, backup_path)
            
            # Rename temp to final (atomic on most filesystems)
            temp_path.replace(self.index_path)
            
            logger.info(f"Saved FAISS index atomically to: {self.index_path}")
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            # Cleanup temp file on error
            temp_path = Path(str(self.index_path) + '.tmp')
            if temp_path.exists():
                temp_path.unlink()
    
    def get_stats(self) -> dict:
        """
        Get statistics about the vector store.
        
        Returns:
            Statistics dictionary
        """
        if not self.is_index_loaded():
            return {
                'total_vectors': 0,
                'dimension': self.dimension,
                'index_loaded': False
            }
        
        return {
            'total_vectors': self.index.ntotal,
            'dimension': self.dimension,
            'index_loaded': True,
            'index_path': str(self.index_path)
        }

