# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_core/loader/hot_swap.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Thread-safe singleton for hot-swapping active models without dropping requests

import threading
from typing import Optional, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HotSwapModelManager:
    """
    Thread-safe singleton that holds the currently active model in memory
    and allows swapping it without dropping API requests.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(HotSwapModelManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the hot-swap manager."""
        if self._initialized:
            return
        
        self._model_lock = threading.RLock()  # Reentrant lock for model access
        self._active_model = None
        self._model_metadata = None
        self._model_id = None
        self._model_type = None
        self._initialized = True
        logger.info("HotSwapModelManager initialized")
    
    def set_active_model(self, model: Any, model_id: int, model_type: str, 
                        metadata: dict = None) -> bool:
        """
        Set the active model (thread-safe).
        
        Args:
            model: The loaded model object
            model_id: Model ID from registry
            model_type: Type of model (pickle, onnx, etc.)
            metadata: Optional model metadata
            
        Returns:
            True if model was set successfully
        """
        with self._model_lock:
            try:
                # Store old model reference for cleanup if needed
                old_model = self._active_model
                old_model_id = self._model_id
                
                # Set new model
                self._active_model = model
                self._model_id = model_id
                self._model_type = model_type
                self._model_metadata = metadata or {}
                
                logger.info(f"Hot-swapped model: ID {old_model_id} -> {model_id} (type: {model_type})")
                
                # Note: We don't explicitly delete old_model here as Python's GC will handle it
                # when there are no more references. This ensures any in-flight requests can
                # still use the old model until they complete.
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to set active model: {e}")
                return False
    
    def get_active_model(self) -> Optional[Any]:
        """
        Get the currently active model (thread-safe).
        
        Returns:
            The active model object, or None if no model is active
        """
        with self._model_lock:
            return self._active_model
    
    def get_model_info(self) -> dict:
        """
        Get information about the active model (thread-safe).
        
        Returns:
            Dictionary with model information
        """
        with self._model_lock:
            if self._active_model is None:
                return {
                    'active': False,
                    'model_id': None,
                    'model_type': None,
                    'metadata': None
                }
            
            return {
                'active': True,
                'model_id': self._model_id,
                'model_type': self._model_type,
                'metadata': self._model_metadata
            }
    
    def is_model_loaded(self) -> bool:
        """
        Check if a model is currently loaded (thread-safe).
        
        Returns:
            True if a model is loaded, False otherwise
        """
        with self._model_lock:
            return self._active_model is not None
    
    def clear_model(self) -> bool:
        """
        Clear the active model (thread-safe).
        
        Returns:
            True if model was cleared successfully
        """
        with self._model_lock:
            old_model_id = self._model_id
            self._active_model = None
            self._model_id = None
            self._model_type = None
            self._model_metadata = None
            
            logger.info(f"Cleared active model (was ID: {old_model_id})")
            return True

# Global singleton instance
_model_manager = None
_manager_lock = threading.Lock()

def get_model_manager() -> HotSwapModelManager:
    """Get or create the global model manager instance."""
    global _model_manager
    if _model_manager is None:
        with _manager_lock:
            if _model_manager is None:
                _model_manager = HotSwapModelManager()
    return _model_manager

