# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant/retriever/embedder.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Wrapper for local embedding model (sentence-transformers or ONNX)

import os
import numpy as np
from pathlib import Path
from typing import List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available, will use mock embeddings")

class Embedder:
    """
    Generates embeddings using local embedding model.
    """
    
    def __init__(self, model_path: str = None):
        """
        Initialize embedder.
        
        Args:
            model_path: Path to embedding model
        """
        self.model_path = Path(model_path or os.environ.get('EMBEDDING_MODEL_PATH', ''))
        self.model = None
        self.model_loaded = False
        self.embedding_dim = 384  # Default dimension
        
        if self.model_path and self.model_path.exists():
            self._load_model()
        else:
            logger.critical(f"Embedding model not found: {self.model_path}. Using mock embeddings.")
    
    def _load_model(self):
        """Load the embedding model."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.critical("sentence-transformers not available, cannot load model")
            return
        
        try:
            logger.info(f"Loading embedding model from: {self.model_path}")
            self.model = SentenceTransformer(str(self.model_path))
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            self.model_loaded = True
            logger.info(f"Embedding model loaded: dimension={self.embedding_dim}")
        except Exception as e:
            logger.critical(f"Failed to load embedding model: {e}. Using mock embeddings.")
            self.model_loaded = False
    
    def is_model_available(self) -> bool:
        """
        Check if model is available.
        
        Returns:
            True if model is loaded, False otherwise
        """
        return self.model_loaded and self.model is not None
    
    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding for text.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as numpy array
        """
        if self.is_model_available():
            try:
                embedding = self.model.encode(text, convert_to_numpy=True)
                return embedding
            except Exception as e:
                logger.error(f"Embedding generation failed: {e}. Using mock embedding.")
                return self._mock_embed(text)
        else:
            return self._mock_embed(text)
    
    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        if self.is_model_available():
            try:
                embeddings = self.model.encode(texts, convert_to_numpy=True)
                return [emb for emb in embeddings]
            except Exception as e:
                logger.error(f"Batch embedding failed: {e}. Using mock embeddings.")
                return [self._mock_embed(text) for text in texts]
        else:
            return [self._mock_embed(text) for text in texts]
    
    def _mock_embed(self, text: str) -> np.ndarray:
        """
        Generate mock embedding (random vector).
        
        Args:
            text: Input text
            
        Returns:
            Mock embedding vector
        """
        # Generate deterministic "random" vector based on text hash
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()
        seed = int(text_hash[:8], 16)
        np.random.seed(seed)
        embedding = np.random.normal(0, 1, self.embedding_dim).astype(np.float32)
        return embedding

