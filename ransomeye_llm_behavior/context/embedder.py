# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/context/embedder.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Wrapper for local embedding model (sentence-transformers or ONNX)

import os
from pathlib import Path
from typing import List, Union
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available. Install: pip install sentence-transformers")

# Try to import ONNX runtime
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logger.warning("onnxruntime not available. ONNX models will not be supported")


class LocalEmbedder:
    """
    Wrapper for local embedding models.
    Supports sentence-transformers and ONNX models.
    """
    
    def __init__(
        self,
        model_name: str = None,
        model_path: str = None,
        use_onnx: bool = False
    ):
        """
        Initialize embedder.
        
        Args:
            model_name: Model name for sentence-transformers (e.g., 'all-MiniLM-L6-v2')
            model_path: Path to local model file (ONNX or sentence-transformers)
            use_onnx: Whether to use ONNX runtime
        """
        self.model = None
        self.model_type = None
        self.embedding_dim = None
        
        if use_onnx and ONNX_AVAILABLE:
            self._load_onnx_model(model_path)
        elif SENTENCE_TRANSFORMERS_AVAILABLE:
            self._load_sentence_transformer(model_name, model_path)
        else:
            logger.warning("No embedding library available. Using fallback hash-based embeddings.")
            self.model_type = 'fallback'
            self.embedding_dim = 256
    
    def _load_sentence_transformer(self, model_name: str = None, model_path: str = None):
        """Load sentence-transformers model."""
        try:
            if model_path and Path(model_path).exists():
                self.model = SentenceTransformer(model_path)
                logger.info(f"Loaded sentence-transformers model from {model_path}")
            elif model_name:
                self.model = SentenceTransformer(model_name)
                logger.info(f"Loaded sentence-transformers model: {model_name}")
            else:
                # Default model
                default_model = 'all-MiniLM-L6-v2'
                self.model = SentenceTransformer(default_model)
                logger.info(f"Loaded default sentence-transformers model: {default_model}")
            
            self.model_type = 'sentence-transformers'
            # Get embedding dimension
            test_embedding = self.model.encode(['test'])
            self.embedding_dim = len(test_embedding[0])
        
        except Exception as e:
            logger.error(f"Error loading sentence-transformers model: {e}")
            self.model_type = 'fallback'
            self.embedding_dim = 256
    
    def _load_onnx_model(self, model_path: str):
        """Load ONNX model."""
        if not ONNX_AVAILABLE:
            logger.warning("ONNX runtime not available")
            return
        
        try:
            if not model_path or not Path(model_path).exists():
                logger.warning(f"ONNX model not found: {model_path}")
                self.model_type = 'fallback'
                return
            
            self.model = ort.InferenceSession(model_path)
            self.model_type = 'onnx'
            # Get embedding dimension from model output shape
            output_shape = self.model.get_outputs()[0].shape
            self.embedding_dim = output_shape[-1] if output_shape else 384
            logger.info(f"Loaded ONNX model from {model_path}, dimension: {self.embedding_dim}")
        
        except Exception as e:
            logger.error(f"Error loading ONNX model: {e}")
            self.model_type = 'fallback'
            self.embedding_dim = 256
    
    def encode(self, texts: Union[str, List[str]], batch_size: int = 32) -> List[List[float]]:
        """
        Encode texts into embeddings.
        
        Args:
            texts: Single text or list of texts
            batch_size: Batch size for encoding
            
        Returns:
            List of embedding vectors
        """
        if isinstance(texts, str):
            texts = [texts]
        
        if self.model_type == 'sentence-transformers' and self.model:
            embeddings = self.model.encode(texts, batch_size=batch_size, show_progress_bar=False)
            return embeddings.tolist() if hasattr(embeddings, 'tolist') else embeddings
        
        elif self.model_type == 'onnx' and self.model:
            # ONNX inference
            embeddings = []
            for text in texts:
                # Preprocess text (would need tokenizer in production)
                # For now, use simple approach
                inputs = {'input_ids': self._text_to_ids(text)}  # Simplified
                outputs = self.model.run(None, inputs)
                embeddings.append(outputs[0].tolist() if hasattr(outputs[0], 'tolist') else outputs[0])
            return embeddings
        
        else:
            # Fallback: hash-based embeddings
            return [self._hash_embedding(text) for text in texts]
    
    def _text_to_ids(self, text: str) -> List[int]:
        """Convert text to token IDs (simplified for ONNX)."""
        # In production, would use proper tokenizer
        # For now, simple character-based encoding
        return [ord(c) % 1000 for c in text[:512]]
    
    def _hash_embedding(self, text: str) -> List[float]:
        """
        Generate hash-based embedding as fallback.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector
        """
        import hashlib
        import struct
        
        # Generate multiple hashes and combine
        embeddings = []
        for i in range(self.embedding_dim // 4):
            hash_input = f"{text}:{i}".encode('utf-8')
            hash_bytes = hashlib.md5(hash_input).digest()
            # Convert to floats
            for j in range(4):
                val = struct.unpack('f', hash_bytes[j*4:(j+1)*4])[0]
                embeddings.append(val)
        
        # Normalize
        norm = sum(x*x for x in embeddings) ** 0.5
        if norm > 0:
            embeddings = [x / norm for x in embeddings]
        
        return embeddings[:self.embedding_dim]
    
    def get_embedding_dim(self) -> int:
        """Get embedding dimension."""
        return self.embedding_dim

