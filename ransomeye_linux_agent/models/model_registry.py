# Path and File Name : /home/ransomeye/rebuild/ransomeye_linux_agent/models/model_registry.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Manages local model versions and updates

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelRegistry:
    """Manages local model versions."""
    
    def __init__(self):
        """Initialize model registry."""
        self.models_dir = Path(os.environ.get(
            'MODEL_DIR',
            '/opt/ransomeye-agent/models'
        ))
        self.registry_file = self.models_dir / 'registry.json'
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._load_registry()
        logger.info("Model registry initialized")
    
    def _load_registry(self):
        """Load model registry."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r') as f:
                    self.registry = json.load(f)
            except Exception as e:
                logger.error(f"Error loading registry: {e}")
                self.registry = {}
        else:
            self.registry = {}
    
    def _save_registry(self):
        """Save model registry."""
        try:
            with open(self.registry_file, 'w') as f:
                json.dump(self.registry, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving registry: {e}")
    
    def register_model(self, model_path: str, version: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Register a new model version.
        
        Args:
            model_path: Path to model file
            version: Model version string
            metadata: Optional metadata
            
        Returns:
            True if successful
        """
        try:
            model_file = Path(model_path)
            if not model_file.exists():
                logger.error(f"Model file not found: {model_path}")
                return False
            
            # Calculate hash
            with open(model_file, 'rb') as f:
                model_hash = hashlib.sha256(f.read()).hexdigest()
            
            # Register
            self.registry[version] = {
                "path": str(model_path),
                "hash_sha256": model_hash,
                "registered_at": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            
            self._save_registry()
            logger.info(f"Model registered: version {version}")
            return True
        
        except Exception as e:
            logger.error(f"Error registering model: {e}")
            return False
    
    def get_model_info(self, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get model information.
        
        Args:
            version: Model version (None for latest)
            
        Returns:
            Model info dictionary
        """
        if not self.registry:
            return None
        
        if version:
            return self.registry.get(version)
        else:
            # Return latest version
            versions = sorted(self.registry.keys(), reverse=True)
            if versions:
                return self.registry[versions[0]]
            return None
    
    def list_models(self) -> List[str]:
        """
        List all registered model versions.
        
        Returns:
            List of version strings
        """
        return sorted(self.registry.keys(), reverse=True)

