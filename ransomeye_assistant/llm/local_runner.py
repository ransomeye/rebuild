# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant/llm/local_runner.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Wrapper for llama-cpp-python (reuses logic from Phase 5)

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import llama-cpp-python
try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False
    logger.warning("llama-cpp-python not available, will use safe fallback mode")

class LocalLLMRunner:
    """
    LLM inference runner with llama-cpp-python support and safe fallback.
    """
    
    def __init__(self, model_path: str = None):
        """
        Initialize LLM runner.
        
        Args:
            model_path: Path to GGUF model file
        """
        self.model_path = Path(model_path or os.environ.get('LLM_MODEL_PATH', ''))
        self.model = None
        self.model_loaded = False
        self.max_tokens = int(os.environ.get('LLM_MAX_TOKENS', '512'))
        self.temperature = float(os.environ.get('LLM_TEMPERATURE', '0.7'))
        
        if self.model_path and self.model_path.exists():
            self._load_model()
        else:
            logger.critical(f"LLM model file not found: {self.model_path}. Using safe fallback mode.")
    
    def _load_model(self):
        """Load the LLM model."""
        if not LLAMA_AVAILABLE:
            logger.critical("llama-cpp-python not available, cannot load model")
            return
        
        try:
            logger.info(f"Loading LLM model from: {self.model_path}")
            self.model = Llama(
                model_path=str(self.model_path),
                n_ctx=2048,
                n_threads=4,
                verbose=False
            )
            self.model_loaded = True
            logger.info("LLM model loaded successfully")
        except Exception as e:
            logger.critical(f"Failed to load LLM model: {e}. Using safe fallback mode.")
            self.model_loaded = False
    
    def is_model_available(self) -> bool:
        """
        Check if model is available.
        
        Returns:
            True if model is loaded, False otherwise
        """
        return self.model_loaded and self.model is not None
    
    def generate(self, prompt: str, max_tokens: Optional[int] = None,
                 temperature: Optional[float] = None) -> Dict[str, Any]:
        """
        Generate text from prompt.
        
        Args:
            prompt: Input prompt text
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Dictionary with generated text and metadata
        """
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature
        
        if not self.is_model_available():
            return self._safe_fallback_generate(prompt)
        
        try:
            start_time = time.time()
            
            response = self.model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=["\n\n", "Human:", "Assistant:"],
                echo=False
            )
            
            inference_time = time.time() - start_time
            generated_text = response['choices'][0]['text'].strip()
            
            return {
                'text': generated_text,
                'model_used': True,
                'inference_time': inference_time,
                'tokens_generated': len(generated_text.split()),
                'fallback': False
            }
            
        except Exception as e:
            logger.error(f"LLM inference failed: {e}. Falling back to safe mode.")
            return self._safe_fallback_generate(prompt)
    
    def _safe_fallback_generate(self, prompt: str) -> Dict[str, Any]:
        """
        Safe fallback generator when model is not available.
        
        Args:
            prompt: Input prompt text
            
        Returns:
            Dictionary with generated text and metadata
        """
        logger.info("Using safe fallback generator (model not available)")
        
        # Extract question from prompt
        if "Question:" in prompt:
            question = prompt.split("Question:")[-1].split("\n")[0].strip()
        else:
            question = "the question"
        
        # Generate simple response
        answer = f"Based on the provided context, I can help answer: {question}. " \
                 f"However, the LLM model is not currently available. " \
                 f"Please review the source documents provided for detailed information."
        
        return {
            'text': answer,
            'model_used': False,
            'inference_time': 0.0,
            'tokens_generated': len(answer.split()),
            'fallback': True
        }

