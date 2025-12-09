# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant_advanced/embedding/mm_embedder.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Multi-modal embedder that concatenates text and image embeddings

import os
import numpy as np
from typing import Optional, List
import logging

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers not available - using mock embeddings")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiModalEmbedder:
    """Multi-modal embedder for text and images."""
    
    def __init__(self, text_model_path: Optional[str] = None):
        """
        Initialize multi-modal embedder.
        
        Args:
            text_model_path: Path to text embedding model
        """
        self.text_model = None
        self.text_model_path = text_model_path or os.environ.get('EMBEDDING_MODEL_PATH', None)
        self.text_dim = 384  # Default dimension
        self.image_dim = 512  # Default image embedding dimension
        self._load_text_model()
    
    def _load_text_model(self):
        """Load text embedding model."""
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                if self.text_model_path and os.path.exists(self.text_model_path):
                    self.text_model = SentenceTransformer(self.text_model_path)
                else:
                    # Use default model
                    self.text_model = SentenceTransformer('all-MiniLM-L6-v2')
                
                # Get actual dimension
                test_embedding = self.text_model.encode("test")
                self.text_dim = len(test_embedding)
                
                logger.info(f"Loaded text embedding model (dim={self.text_dim})")
            except Exception as e:
                logger.error(f"Error loading text model: {e}")
                self.text_model = None
        else:
            logger.warning("sentence-transformers not available - using mock embeddings")
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Embed text.
        
        Args:
            text: Text to embed
            
        Returns:
            Text embedding vector
        """
        if self.text_model:
            try:
                embedding = self.text_model.encode(text, convert_to_numpy=True)
                return embedding
            except Exception as e:
                logger.error(f"Error embedding text: {e}")
                return self._mock_embedding(self.text_dim, text)
        else:
            return self._mock_embedding(self.text_dim, text)
    
    def embed_image(self, image_path: str) -> np.ndarray:
        """
        Embed image (placeholder - would use CLIP or similar in production).
        
        Args:
            image_path: Path to image file
            
        Returns:
            Image embedding vector
        """
        # In production, this would use CLIP or similar vision encoder
        # For now, return mock embedding based on file hash
        import hashlib
        
        with open(image_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        # Generate deterministic mock embedding from hash
        np.random.seed(int(file_hash[:8], 16))
        embedding = np.random.normal(0, 1, self.image_dim).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)  # Normalize
        
        return embedding
    
    def embed_multimodal(self, text: Optional[str] = None, image_path: Optional[str] = None) -> np.ndarray:
        """
        Embed multi-modal input (text + image).
        
        Args:
            text: Optional text
            image_path: Optional image path
            
        Returns:
            Concatenated multi-modal embedding
        """
        embeddings = []
        
        if text:
            text_emb = self.embed_text(text)
            embeddings.append(text_emb)
        
        if image_path:
            image_emb = self.embed_image(image_path)
            embeddings.append(image_emb)
        
        if not embeddings:
            # Return zero vector if no inputs
            return np.zeros(self.text_dim + self.image_dim, dtype=np.float32)
        
        # Concatenate embeddings
        combined = np.concatenate(embeddings)
        
        # Normalize
        norm = np.linalg.norm(combined)
        if norm > 0:
            combined = combined / norm
        
        return combined
    
    def _mock_embedding(self, dim: int, seed: str) -> np.ndarray:
        """
        Generate mock embedding (deterministic).
        
        Args:
            dim: Embedding dimension
            seed: Seed string
            
        Returns:
            Mock embedding vector
        """
        # Generate deterministic embedding from seed
        import hashlib
        seed_hash = int(hashlib.md5(seed.encode()).hexdigest()[:8], 16)
        np.random.seed(seed_hash)
        embedding = np.random.normal(0, 1, dim).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)
        return embedding

