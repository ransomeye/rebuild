# Path and File Name : /home/ransomeye/rebuild/ransomeye_windows_agent/models/model_registry.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Model version management and registry for tracking model versions and metadata

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelRegistry:
    """Manages model versions and metadata."""
    
    def __init__(self):
        """Initialize model registry."""
        model_base = os.path.join(
            os.environ.get('PROGRAMDATA', 'C:\\ProgramData'),
            'RansomEye',
            'models'
        )
        
        self.registry_path = Path(model_base) / 'registry.json'
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.registry = self._load_registry()
        logger.info("Model registry initialized")
    
    def _load_registry(self) -> Dict[str, Any]:
        """Load registry from disk."""
        try:
            if self.registry_path.exists():
                with open(self.registry_path, 'r') as f:
                    return json.load(f)
            else:
                return {"models": {}}
        except Exception as e:
            logger.error(f"Error loading registry: {e}")
            return {"models": {}}
    
    def _save_registry(self):
        """Save registry to disk."""
        try:
            with open(self.registry_path, 'w') as f:
                json.dump(self.registry, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving registry: {e}")
    
    def register_model(self, model_path: Path, version: str, metadata: Dict[str, Any] = None):
        """
        Register a model in the registry.
        
        Args:
            model_path: Path to model file
            version: Model version string
            metadata: Additional metadata
        """
        try:
            # Calculate hash
            model_hash = self._calculate_hash(model_path)
            
            model_info = {
                "path": str(model_path),
                "version": version,
                "hash": model_hash,
                "metadata": metadata or {}
            }
            
            if "models" not in self.registry:
                self.registry["models"] = {}
            
            self.registry["models"][version] = model_info
            self._save_registry()
            
            logger.info(f"Model registered: {version} ({model_hash[:16]}...)")
        
        except Exception as e:
            logger.error(f"Error registering model: {e}")
    
    def get_model_info(self, version: str) -> Optional[Dict[str, Any]]:
        """
        Get model information by version.
        
        Args:
            version: Model version string
            
        Returns:
            Model information dictionary or None
        """
        return self.registry.get("models", {}).get(version)
    
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

