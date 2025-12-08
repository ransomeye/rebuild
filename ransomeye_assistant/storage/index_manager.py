# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant/storage/index_manager.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Manages versions of FAISS index with atomic swap

import os
import shutil
from pathlib import Path
from typing import List
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IndexManager:
    """
    Manages FAISS index versions with atomic swap.
    """
    
    def __init__(self, data_dir: str = None):
        """
        Initialize index manager.
        
        Args:
            data_dir: Data directory for index storage
        """
        self.data_dir = Path(data_dir or os.environ.get(
            'ASSISTANT_DATA_DIR',
            '/home/ransomeye/rebuild/ransomeye_assistant/data'
        ))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.index_path = self.data_dir / "index.faiss"
        self.temp_index_path = self.data_dir / "index.faiss.tmp"
        self.id_map_path = self.data_dir / "index_ids.json"
    
    def add_vectors(self, chunk_ids: List[str], embeddings: List[np.ndarray]):
        """
        Add vectors to index (atomic operation).
        
        This method coordinates with VectorStore for atomic index updates.
        The actual atomic operation is handled in vector_store.save_index().
        
        Args:
            chunk_ids: List of chunk identifiers
            embeddings: List of embedding vectors
        """
        # Import here to avoid circular dependency
        from ..retriever.vector_store import VectorStore
        
        # Load or create vector store
        vector_store = VectorStore(index_path=str(self.index_path))
        
        # Add vectors
        vector_store.add_vectors(chunk_ids, embeddings)
        
        # Save with atomic operation
        vector_store.save_index()
        
        logger.info(f"Index manager: Added {len(chunk_ids)} vectors atomically")

