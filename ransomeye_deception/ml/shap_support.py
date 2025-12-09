# Path and File Name : /home/ransomeye/rebuild/ransomeye_deception/ml/shap_support.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Generates SHAP JSON explanations for placement decisions

import os
import sys
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import SHAP
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("SHAP not available, explanations will be simplified")


class SHAPSupport:
    """
    SHAP explanation support for placement decisions.
    """
    
    def __init__(self):
        """Initialize SHAP support."""
        self.feature_names = [
            'host_criticality',
            'segment_hash',
            'existing_density',
            'decoy_type_hash',
            'type_specific_feature'
        ]
        logger.info("SHAP support initialized")
    
    async def explain_placement(self, features: np.ndarray, score: float,
                               decoy_type: str) -> Dict[str, Any]:
        """
        Generate SHAP explanation for placement decision.
        
        Args:
            features: Feature vector
            score: Predicted attractiveness score
            decoy_type: Type of decoy
            
        Returns:
            SHAP explanation dictionary
        """
        try:
            if not SHAP_AVAILABLE:
                return self._simple_explanation(features, score)
            
            # Get model from placement model
            from .placement_model import PlacementModel
            
            model_instance = PlacementModel()
            model = model_instance.model
            
            if model is None:
                return self._simple_explanation(features, score)
            
            # Ensure features are 2D
            if features.ndim == 1:
                features_2d = features.reshape(1, -1)
            else:
                features_2d = features
            
            # Create SHAP explainer
            try:
                if hasattr(model, 'tree_') or hasattr(model, 'estimators_'):
                    # Tree-based model
                    explainer = shap.TreeExplainer(model)
                    shap_values = explainer.shap_values(features_2d)
                    base_value = explainer.expected_value
                else:
                    # Other models - use KernelExplainer
                    explainer = shap.KernelExplainer(
                        model.predict,
                        features_2d[:1]  # Background data
                    )
                    shap_values = explainer.shap_values(features_2d[0])
                    base_value = explainer.expected_value
            except Exception as e:
                logger.warning(f"SHAP explainer failed: {e}, using simple explanation")
                return self._simple_explanation(features, score)
            
            # Handle array outputs
            if isinstance(shap_values, list):
                shap_values = shap_values[0] if len(shap_values) > 0 else shap_values
            
            # Extract values for first instance
            if isinstance(shap_values, np.ndarray) and shap_values.ndim > 1:
                shap_vals = shap_values[0]
            else:
                shap_vals = shap_values
            
            # Build explanation dictionary
            shap_dict = {}
            for i, name in enumerate(self.feature_names):
                if i < len(shap_vals):
                    shap_dict[name] = float(shap_vals[i])
            
            return {
                'shap_values': shap_dict,
                'base_value': float(base_value) if isinstance(base_value, (int, float, np.number)) else 0.0,
                'prediction': float(score),
                'feature_names': self.feature_names,
                'method': 'TreeExplainer' if hasattr(model, 'tree_') else 'KernelExplainer'
            }
            
        except Exception as e:
            logger.error(f"Error generating SHAP explanation: {e}")
            return self._simple_explanation(features, score)
    
    def _simple_explanation(self, features: np.ndarray, score: float) -> Dict[str, Any]:
        """
        Generate simple explanation without SHAP.
        
        Args:
            features: Feature vector
            score: Predicted score
            
        Returns:
            Simple explanation dictionary
        """
        # Create simple feature contributions based on feature values
        shap_dict = {}
        for i, name in enumerate(self.feature_names):
            if i < len(features):
                # Simple heuristic: contribution proportional to feature value
                contribution = float(features[i]) * (score / len(features))
                shap_dict[name] = contribution
        
        return {
            'shap_values': shap_dict,
            'base_value': 0.0,
            'prediction': float(score),
            'feature_names': self.feature_names,
            'method': 'heuristic'
        }

