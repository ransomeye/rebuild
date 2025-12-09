# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/explain/explanation_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Stores SHAP JSON explanations

import os
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExplanationStore:
    """
    Stores SHAP explanations for model predictions.
    """
    
    def __init__(self, storage_dir: str = None):
        """Initialize explanation store."""
        if storage_dir is None:
            storage_dir = os.environ.get(
                'EXPLANATION_DIR',
                '/home/ransomeye/rebuild/ransomeye_llm_behavior/explain/storage'
            )
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def save_explanation(
        self,
        explanation_id: str,
        shap_values: Dict,
        metadata: Dict = None
    ):
        """Save SHAP explanation."""
        explanation_data = {
            'explanation_id': explanation_id,
            'shap_values': shap_values,
            'metadata': metadata or {},
            'created_at': datetime.utcnow().isoformat()
        }
        
        explanation_file = self.storage_dir / f"{explanation_id}.json"
        with open(explanation_file, 'w') as f:
            json.dump(explanation_data, f, indent=2)
        
        logger.info(f"Saved explanation: {explanation_id}")
    
    def load_explanation(self, explanation_id: str) -> Optional[Dict]:
        """Load SHAP explanation."""
        explanation_file = self.storage_dir / f"{explanation_id}.json"
        
        if not explanation_file.exists():
            return None
        
        try:
            with open(explanation_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading explanation: {e}")
            return None

