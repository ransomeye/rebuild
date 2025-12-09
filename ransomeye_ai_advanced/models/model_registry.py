# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/models/model_registry.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Local model versioning and registry

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Registry for managing model versions and metadata.
    """
    
    def __init__(self, registry_path: Optional[str] = None):
        """
        Initialize model registry.
        
        Args:
            registry_path: Path to registry JSON file
        """
        self.registry_path = registry_path or os.environ.get(
            'MODEL_REGISTRY_PATH',
            str(Path(__file__).parent / 'model_registry.json')
        )
        self.registry: Dict[str, Any] = {}
        self._load_registry()
    
    def _load_registry(self):
        """Load registry from file."""
        if os.path.exists(self.registry_path):
            try:
                with open(self.registry_path, 'r') as f:
                    self.registry = json.load(f)
                logger.info(f"Loaded model registry from {self.registry_path}")
            except Exception as e:
                logger.error(f"Error loading registry: {e}")
                self.registry = {'models': {}}
        else:
            self.registry = {'models': {}}
            self._save_registry()
    
    def _save_registry(self):
        """Save registry to file."""
        try:
            os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
            with open(self.registry_path, 'w') as f:
                json.dump(self.registry, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving registry: {e}")
    
    def register_model(
        self,
        model_name: str,
        model_path: str,
        model_type: str,
        version: str = "1.0.0",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Register a model in the registry.
        
        Args:
            model_name: Name of model
            model_path: Path to model file
            model_type: Type of model (e.g., 'validator', 'reranker')
            version: Model version
            metadata: Optional metadata
            
        Returns:
            Model ID
        """
        # Calculate hash
        if os.path.exists(model_path):
            with open(model_path, 'rb') as f:
                model_hash = hashlib.sha256(f.read()).hexdigest()
        else:
            model_hash = 'unknown'
        
        model_id = f"{model_name}_{version}"
        
        model_entry = {
            'model_id': model_id,
            'model_name': model_name,
            'model_path': model_path,
            'model_type': model_type,
            'version': version,
            'hash': model_hash,
            'metadata': metadata or {},
            'registered_at': datetime.utcnow().isoformat()
        }
        
        if 'models' not in self.registry:
            self.registry['models'] = {}
        
        self.registry['models'][model_id] = model_entry
        self._save_registry()
        
        logger.info(f"Registered model: {model_id}")
        return model_id
    
    def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model by ID."""
        return self.registry.get('models', {}).get(model_id)
    
    def list_models(self, model_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all models, optionally filtered by type."""
        models = list(self.registry.get('models', {}).values())
        if model_type:
            models = [m for m in models if m.get('model_type') == model_type]
        return models
    
    def get_latest_version(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get latest version of a model."""
        models = [
            m for m in self.registry.get('models', {}).values()
            if m.get('model_name') == model_name
        ]
        if not models:
            return None
        # Sort by version (simplified)
        return max(models, key=lambda m: m.get('version', '0.0.0'))

