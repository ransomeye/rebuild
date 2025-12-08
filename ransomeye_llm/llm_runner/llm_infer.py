# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm/llm_runner/llm_infer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Wrapper for llama-cpp-python with safe fallback mode

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
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

class LLMInferenceEngine:
    """
    LLM inference engine with llama-cpp-python support and safe fallback.
    """
    
    def __init__(self, model_path: str = None):
        """
        Initialize LLM inference engine.
        
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
            logger.critical(f"Model file not found: {self.model_path}. Using safe fallback mode.")
    
    def _load_model(self):
        """Load the LLM model."""
        if not LLAMA_AVAILABLE:
            logger.critical("llama-cpp-python not available, cannot load model")
            return
        
        try:
            logger.info(f"Loading LLM model from: {self.model_path}")
            self.model = Llama(
                model_path=str(self.model_path),
                n_ctx=2048,  # Context window
                n_threads=4,  # CPU threads
                verbose=False
            )
            self.model_loaded = True
            logger.info("LLM model loaded successfully")
        except Exception as e:
            logger.critical(f"Failed to load LLM model: {e}. Using safe fallback mode.")
            self.model_loaded = False
    
    def is_model_available(self) -> bool:
        """
        Check if model is available and loaded.
        
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
            max_tokens: Maximum tokens to generate (overrides default)
            temperature: Sampling temperature (overrides default)
            
        Returns:
            Dictionary with generated text and metadata
        """
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature
        
        if not self.is_model_available():
            return self._safe_fallback_generate(prompt)
        
        try:
            start_time = time.time()
            
            # Generate with llama-cpp-python
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
        Generates a rule-based summary.
        
        Args:
            prompt: Input prompt text
            
        Returns:
            Dictionary with generated text and metadata
        """
        logger.info("Using safe fallback generator (model not available)")
        
        # Extract key information from prompt
        prompt_lower = prompt.lower()
        
        # Rule-based generation
        summary_parts = []
        
        if 'executive' in prompt_lower or 'brief' in prompt_lower:
            summary_parts.append("## Executive Summary")
            summary_parts.append("\nThis incident report was generated using safe fallback mode.")
            summary_parts.append("The LLM model is not currently available.")
            summary_parts.append("\n### Key Findings:")
            summary_parts.append("- Incident detected and analyzed")
            summary_parts.append("- Security controls activated")
            summary_parts.append("- Investigation in progress")
        
        elif 'manager' in prompt_lower or 'timeline' in prompt_lower:
            summary_parts.append("## Manager Summary")
            summary_parts.append("\nThis report was generated using safe fallback mode.")
            summary_parts.append("\n### Timeline Overview:")
            summary_parts.append("- Initial detection occurred")
            summary_parts.append("- Response actions were taken")
            summary_parts.append("- Investigation continues")
        
        elif 'analyst' in prompt_lower or 'technical' in prompt_lower:
            summary_parts.append("## Technical Analysis")
            summary_parts.append("\n**Note:** This report was generated using safe fallback mode.")
            summary_parts.append("The LLM model is not available for advanced analysis.")
            summary_parts.append("\n### Technical Details:")
            summary_parts.append("- Analysis performed using rule-based engine")
            summary_parts.append("- Full LLM analysis requires model file")
            summary_parts.append("- IOCs and SHAP values should be reviewed manually")
        
        else:
            summary_parts.append("## Summary")
            summary_parts.append("\nThis report was generated using safe fallback mode.")
            summary_parts.append("The LLM model is not currently available.")
        
        summary_parts.append("\n\n**Model Status:** Not Loaded")
        summary_parts.append("**Generation Mode:** Safe Fallback")
        
        generated_text = "\n".join(summary_parts)
        
        return {
            'text': generated_text,
            'model_used': False,
            'inference_time': 0.0,
            'tokens_generated': len(generated_text.split()),
            'fallback': True
        }
    
    def generate_summary(self, context: Dict[str, Any], template_type: str = "executive") -> Dict[str, Any]:
        """
        Generate summary from context data.
        
        Args:
            context: Context dictionary with incident data
            template_type: Type of template (executive, manager, analyst)
            
        Returns:
            Dictionary with generated summary and metadata
        """
        # Build prompt from context
        prompt = self._build_prompt(context, template_type)
        
        # Generate
        result = self.generate(prompt)
        
        return result
    
    def _build_prompt(self, context: Dict[str, Any], template_type: str) -> str:
        """
        Build prompt from context.
        
        Args:
            context: Context dictionary
            template_type: Type of template
            
        Returns:
            Prompt string
        """
        prompt_parts = []
        
        # Add context information
        if 'incident_id' in context:
            prompt_parts.append(f"Incident ID: {context['incident_id']}")
        
        if 'alerts' in context:
            alert_count = len(context['alerts'])
            prompt_parts.append(f"Total Alerts: {alert_count}")
        
        if 'timeline' in context:
            prompt_parts.append("Timeline data available")
        
        if 'shap_values' in context:
            prompt_parts.append("SHAP feature importance data available")
        
        # Add instruction based on template type
        if template_type == "executive":
            prompt_parts.append("\nGenerate a brief executive summary focusing on business impact.")
        elif template_type == "manager":
            prompt_parts.append("\nGenerate a manager-level summary with timeline and key events.")
        elif template_type == "analyst":
            prompt_parts.append("\nGenerate a technical analyst summary with IOCs and SHAP analysis.")
        
        return "\n".join(prompt_parts)

