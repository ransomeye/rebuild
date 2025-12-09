# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/ml/model_registry.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Local registry for managing forensic model versions and metadata

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Registry for managing forensic ML model versions.
    Tracks model metadata, versions, and SHAP explainability files.
    """
    
    def __init__(self, registry_path: Optional[str] = None):
        """
        Initialize model registry.
        
        Args:
            registry_path: Path to registry directory
        """
        if registry_path is None:
            registry_path = os.environ.get(
                'MODEL_DIR',
                '/home/ransomeye/rebuild/ransomeye_forensic/ml/models'
            )
        
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(parents=True, exist_ok=True)
        
        self.metadata_file = self.registry_path / 'registry.json'
        self.registry = self._load_registry()
    
    def _load_registry(self) -> Dict:
        """Load registry from file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading registry: {e}")
        
        return {
            'models': {},
            'active_model': None,
            'version': '1.0'
        }
    
    def _save_registry(self):
        """Save registry to file."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.registry, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving registry: {e}")
    
    def register_model(
        self,
        model_id: str,
        model_path: str,
        model_type: str = 'classifier',
        version: str = '1.0',
        shap_path: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Register a new model in the registry.
        
        Args:
            model_id: Unique model identifier
            model_path: Path to model file (.pkl, .gguf, etc.)
            model_type: Type of model ('classifier', 'fingerprinter', etc.)
            version: Model version string
            shap_path: Path to SHAP explainability file (optional)
            metadata: Additional metadata dictionary
            
        Returns:
            True if registration successful
        """
        model_path_obj = Path(model_path)
        if not model_path_obj.exists():
            logger.error(f"Model file not found: {model_path}")
            return False
        
        # Compute model hash
        model_hash = self._compute_file_hash(model_path)
        
        # Verify SHAP file if provided
        shap_hash = None
        if shap_path:
            shap_path_obj = Path(shap_path)
            if shap_path_obj.exists():
                shap_hash = self._compute_file_hash(shap_path)
            else:
                logger.warning(f"SHAP file not found: {shap_path}")
        
        # Register model
        model_entry = {
            'model_id': model_id,
            'model_path': str(model_path),
            'model_type': model_type,
            'version': version,
            'model_hash': model_hash,
            'shap_path': shap_path,
            'shap_hash': shap_hash,
            'registered_at': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        
        if 'models' not in self.registry:
            self.registry['models'] = {}
        
        self.registry['models'][model_id] = model_entry
        
        # Set as active if first model
        if self.registry['active_model'] is None:
            self.registry['active_model'] = model_id
        
        self._save_registry()
        logger.info(f"Registered model: {model_id} (version {version})")
        
        return True
    
    def get_model(self, model_id: Optional[str] = None) -> Optional[Dict]:
        """
        Get model entry from registry.
        
        Args:
            model_id: Model ID (uses active model if None)
            
        Returns:
            Model entry dictionary or None
        """
        if model_id is None:
            model_id = self.registry.get('active_model')
        
        if model_id is None:
            return None
        
        return self.registry.get('models', {}).get(model_id)
    
    def set_active_model(self, model_id: str) -> bool:
        """
        Set active model.
        
        Args:
            model_id: Model ID to activate
            
        Returns:
            True if successful
        """
        if model_id not in self.registry.get('models', {}):
            logger.error(f"Model not found: {model_id}")
            return False
        
        self.registry['active_model'] = model_id
        self._save_registry()
        logger.info(f"Set active model: {model_id}")
        
        return True
    
    def list_models(self) -> List[Dict]:
        """
        List all registered models.
        
        Returns:
            List of model entries
        """
        models = self.registry.get('models', {})
        return list(models.values())
    
    def verify_model(self, model_id: Optional[str] = None) -> Dict:
        """
        Verify model integrity (check file exists and hash matches).
        
        Args:
            model_id: Model ID (uses active model if None)
            
        Returns:
            Verification results
        """
        model_entry = self.get_model(model_id)
        if model_entry is None:
            return {
                'valid': False,
                'error': 'Model not found'
            }
        
        model_path = Path(model_entry['model_path'])
        if not model_path.exists():
            return {
                'valid': False,
                'error': 'Model file not found',
                'model_path': str(model_path)
            }
        
        # Verify hash
        current_hash = self._compute_file_hash(str(model_path))
        if current_hash != model_entry['model_hash']:
            return {
                'valid': False,
                'error': 'Model hash mismatch',
                'expected': model_entry['model_hash'],
                'actual': current_hash
            }
        
        # Verify SHAP if present
        shap_valid = True
        if model_entry.get('shap_path'):
            shap_path = Path(model_entry['shap_path'])
            if not shap_path.exists():
                shap_valid = False
            else:
                current_shap_hash = self._compute_file_hash(str(shap_path))
                if current_shap_hash != model_entry.get('shap_hash'):
                    shap_valid = False
        
        return {
            'valid': True,
            'model_hash_match': True,
            'shap_valid': shap_valid,
            'model_id': model_entry['model_id'],
            'version': model_entry['version']
        }
    
    def _compute_file_hash(self, file_path: str) -> str:
        """Compute SHA256 hash of file."""
        hash_obj = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()

