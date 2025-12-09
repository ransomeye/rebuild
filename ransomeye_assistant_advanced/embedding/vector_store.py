# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant_advanced/embedding/vector_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: FAISS vector store for multi-modal embeddings

import os
from pathlib import Path
from typing import List, Tuple, Optional
import numpy as np
import logging

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logging.warning("faiss-cpu not available - vector store disabled")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorStore:
    """FAISS vector store for multi-modal embeddings."""
    
    def __init__(self, index_path: Optional[str] = None, dimension: int = 896):
        """
        Initialize vector store.
        
        Args:
            index_path: Path to FAISS index file
            dimension: Embedding dimension (text + image)
        """
        self.index_path = index_path or os.environ.get('VECTOR_INDEX_PATH', '/var/lib/ransomeye/assistant_advanced/index.faiss')
        self.dimension = dimension
        self.index = None
        self.id_map = {}  # FAISS ID -> artifact_id
        self.reverse_map = {}  # artifact_id -> FAISS ID
        
        if FAISS_AVAILABLE:
            self._load_or_create_index()
        else:
            logger.warning("FAISS not available - vector store disabled")
    
    def _load_or_create_index(self):
        """Load existing index or create new one."""
        index_file = Path(self.index_path)
        
        if index_file.exists():
            try:
                self.index = faiss.read_index(str(index_file))
                logger.info(f"Loaded FAISS index from {self.index_path} ({self.index.ntotal} vectors)")
                
                # Load ID mapping if available
                mapping_path = Path(self.index_path).with_suffix('.mapping')
                if mapping_path.exists():
                    import json
                    with open(mapping_path, 'r') as f:
                        self.id_map = json.load(f)
                        self.reverse_map = {v: k for k, v in self.id_map.items()}
            except Exception as e:
                logger.error(f"Error loading index: {e}")
                self._create_index()
        else:
            self._create_index()
    
    def _create_index(self):
        """Create new FAISS index."""
        if not FAISS_AVAILABLE:
            return
        
        # Create L2 distance index
        self.index = faiss.IndexFlatL2(self.dimension)
        logger.info(f"Created new FAISS index (dim={self.dimension})")
    
    def add_vectors(self, artifact_ids: List[str], embeddings: List[np.ndarray]):
        """
        Add vectors to index.
        
        Args:
            artifact_ids: List of artifact IDs
            embeddings: List of embedding vectors
        """
        if not FAISS_AVAILABLE or not self.index:
            logger.warning("FAISS not available - cannot add vectors")
            return
        
        if len(artifact_ids) != len(embeddings):
            raise ValueError("Number of artifact IDs must match number of embeddings")
        
        # Convert to numpy array
        embedding_matrix = np.array(embeddings).astype('float32')
        
        # Add to index
        start_id = self.index.ntotal
        self.index.add(embedding_matrix)
        
        # Update ID mappings
        for i, artifact_id in enumerate(artifact_ids):
            faiss_id = start_id + i
            self.id_map[str(faiss_id)] = artifact_id
            self.reverse_map[artifact_id] = faiss_id
        
        logger.info(f"Added {len(artifact_ids)} vectors to index")
    
    def search(self, query_embedding: np.ndarray, k: int = 10) -> Tuple[List[str], List[float]]:
        """
        Search for similar vectors.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            
        Returns:
            Tuple of (artifact_ids, distances)
        """
        if not FAISS_AVAILABLE or not self.index:
            return [], []
        
        # Reshape query to 2D
        query = query_embedding.reshape(1, -1).astype('float32')
        
        # Search
        distances, indices = self.index.search(query, k)
        
        # Map FAISS IDs to artifact IDs
        artifact_ids = []
        distances_list = []
        
        for idx, dist in zip(indices[0], distances[0]):
            if idx >= 0:  # Valid index
                artifact_id = self.id_map.get(str(idx))
                if artifact_id:
                    artifact_ids.append(artifact_id)
                    distances_list.append(float(dist))
        
        return artifact_ids, distances_list
    
    def save_index(self):
        """Save index to disk."""
        if not FAISS_AVAILABLE or not self.index:
            return
        
        try:
            # Save index atomically
            index_file = Path(self.index_path)
            index_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save to temp file first
            temp_path = index_file.with_suffix('.tmp')
            faiss.write_index(self.index, str(temp_path))
            
            # Atomic rename
            temp_path.replace(index_file)
            
            # Save ID mapping
            mapping_path = index_file.with_suffix('.mapping')
            import json
            with open(mapping_path, 'w') as f:
                json.dump(self.id_map, f)
            
            logger.info(f"Saved FAISS index to {self.index_path}")
            
        except Exception as e:
            logger.error(f"Error saving index: {e}")
    
    def get_stats(self) -> dict:
        """Get index statistics."""
        if not self.index:
            return {'total_vectors': 0}
        
        return {
            'total_vectors': self.index.ntotal,
            'dimension': self.dimension
        }

