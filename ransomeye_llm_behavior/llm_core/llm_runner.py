# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/llm_core/llm_runner.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Local LLM runner with deterministic mode support (llama-cpp wrapper)

import os
from pathlib import Path
from typing import Dict, Optional, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import llama-cpp-python
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    logger.warning("llama-cpp-python not available. Install: pip install llama-cpp-python")


class LLMRunner:
    """
    Local LLM runner with deterministic mode support.
    Wraps llama-cpp-python for offline inference.
    """
    
    def __init__(
        self,
        model_path: str = None,
        n_ctx: int = 2048,
        n_threads: int = None
    ):
        """
        Initialize LLM runner.
        
        Args:
            model_path: Path to GGUF model file
            n_ctx: Context window size
            n_threads: Number of threads (None = auto)
        """
        self.model_path = model_path or os.environ.get('LLM_MODEL_PATH')
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.model = None
        
        if self.model_path and Path(self.model_path).exists():
            self._load_model()
        else:
            logger.warning("No model path provided. Runner will use mock mode.")
    
    def _load_model(self):
        """Load LLM model."""
        if not LLAMA_CPP_AVAILABLE:
            logger.warning("llama-cpp-python not available. Using mock mode.")
            return
        
        try:
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                verbose=False
            )
            logger.info(f"Loaded LLM model from {self.model_path}")
        except Exception as e:
            logger.error(f"Error loading LLM model: {e}")
            self.model = None
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        deterministic: bool = False,
        seed: int = None
    ) -> Dict:
        """
        Generate text from prompt.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1, lower = more deterministic)
            top_p: Nucleus sampling parameter
            deterministic: Whether to use deterministic mode (temperature=0, fixed seed)
            seed: Random seed (used if deterministic=True)
            
        Returns:
            Dictionary with generated text and metadata
        """
        # Enforce deterministic mode
        if deterministic:
            temperature = 0.0
            if seed is None:
                seed = 42  # Default seed for determinism
        
        if self.model and LLAMA_CPP_AVAILABLE:
            return self._generate_with_llama(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                seed=seed
            )
        else:
            return self._generate_mock(prompt, max_tokens, deterministic)
    
    def _generate_with_llama(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
        seed: Optional[int]
    ) -> Dict:
        """Generate using llama-cpp-python."""
        try:
            # Set seed if provided
            if seed is not None:
                import random
                random.seed(seed)
            
            response = self.model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                echo=False,
                stop=["</s>", "\n\n\n"]
            )
            
            generated_text = response['choices'][0]['text']
            
            return {
                'text': generated_text,
                'tokens_generated': response.get('usage', {}).get('completion_tokens', 0),
                'model': self.model_path,
                'deterministic': temperature == 0.0,
                'seed': seed
            }
        
        except Exception as e:
            logger.error(f"Error generating with LLM: {e}")
            return self._generate_mock(prompt, max_tokens, deterministic=(temperature == 0.0))
    
    def _generate_mock(self, prompt: str, max_tokens: int, deterministic: bool) -> Dict:
        """
        Mock generation for testing (when model unavailable).
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens
            deterministic: Whether deterministic
            
        Returns:
            Mock response
        """
        if deterministic:
            # Deterministic mock: hash-based
            import hashlib
            hash_val = hashlib.md5(prompt.encode()).hexdigest()
            mock_text = f"[MOCK RESPONSE] Based on prompt hash: {hash_val[:16]}"
        else:
            mock_text = "[MOCK RESPONSE] This is a mock response. Install llama-cpp-python and provide a model for real generation."
        
        return {
            'text': mock_text[:max_tokens * 4],  # Rough token estimate
            'tokens_generated': len(mock_text.split()),
            'model': 'mock',
            'deterministic': deterministic,
            'seed': 42 if deterministic else None
        }
    
    def is_available(self) -> bool:
        """Check if LLM is available."""
        return self.model is not None and LLAMA_CPP_AVAILABLE

