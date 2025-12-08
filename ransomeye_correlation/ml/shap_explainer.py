# Path and File Name : /home/ransomeye/rebuild/ransomeye_correlation/ml/shap_explainer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Uses shap.TreeExplainer to explain confidence score predictions

import numpy as np
from typing import Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import SHAP
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("SHAP not available, explanations will not be generated")

class SHAPExplainer:
    """
    Generates SHAP explanations for confidence predictions.
    """
    
    def __init__(self):
        """Initialize SHAP explainer."""
        pass
    
    def explain(self, graph_data: Dict[str, Any], confidence_score: float,
                model=None, features: Optional[np.ndarray] = None) -> Optional[Dict[str, Any]]:
        """
        Generate SHAP explanation for confidence score.
        
        Args:
            graph_data: Graph data dictionary
            confidence_score: Predicted confidence score
            model: ML model (optional, will extract from predictor if not provided)
            features: Feature vector (optional, will extract if not provided)
            
        Returns:
            SHAP explanation dictionary or None
        """
        if not SHAP_AVAILABLE:
            return None
        
        try:
            from ..ml.confidence_predictor import ConfidencePredictor
            
            # Get model and features if not provided
            if model is None:
                predictor = ConfidencePredictor()
                model = predictor.model
                if features is None:
                    features = predictor._extract_features(graph_data)
            
            if model is None or features is None:
                return None
            
            # Create SHAP explainer
            explainer = shap.TreeExplainer(model) if hasattr(model, 'tree_') else shap.LinearExplainer(model, features)
            
            # Calculate SHAP values
            shap_values = explainer.shap_values(features)
            
            # Feature names
            feature_names = [
                'num_hosts',
                'alert_severity_sum',
                'distinct_users',
                'time_span'
            ]
            
            # Format SHAP values
            if isinstance(shap_values, list):
                shap_values = shap_values[0]
            
            shap_dict = {}
            for name, value in zip(feature_names, shap_values[0]):
                shap_dict[name] = float(value)
            
            return {
                'shap_values': shap_dict,
                'base_value': float(explainer.expected_value) if hasattr(explainer, 'expected_value') else 0.0,
                'confidence_score': float(confidence_score)
            }
            
        except Exception as e:
            logger.error(f"Error generating SHAP explanation: {e}")
            return None

