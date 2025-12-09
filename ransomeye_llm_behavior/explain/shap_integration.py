# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/explain/shap_integration.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Generates SHAP values for confidence estimator

import logging
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import SHAP
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("SHAP not available. Install: pip install shap")


class SHAPIntegration:
    """
    Integration for SHAP explainability.
    Generates SHAP values for model predictions.
    """
    
    @staticmethod
    def explain_confidence(confidence_estimator, features, model_output) -> Optional[Dict]:
        """
        Generate SHAP explanation for confidence estimate.
        
        Args:
            confidence_estimator: ConfidenceEstimator instance
            features: Feature vector
            model_output: Model prediction output
            
        Returns:
            SHAP values dictionary or None
        """
        if not SHAP_AVAILABLE or confidence_estimator.model is None:
            return None
        
        try:
            if hasattr(confidence_estimator.model, 'tree_'):
                explainer = shap.TreeExplainer(confidence_estimator.model)
                shap_values = explainer.shap_values(features)
                
                if isinstance(shap_values, list):
                    shap_values = shap_values[0]
                
                return {
                    'shap_values': shap_values.tolist() if hasattr(shap_values, 'tolist') else shap_values,
                    'base_value': float(explainer.expected_value) if hasattr(explainer, 'expected_value') else 0.0
                }
        except Exception as e:
            logger.error(f"Error generating SHAP explanation: {e}")
            return None

