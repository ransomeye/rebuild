# Path and File Name : /home/ransomeye/rebuild/ransomeye_windows_agent/models/shap_support.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Generates SHAP JSON explanations for alerts

import os
import numpy as np
from typing import Dict, Any, Optional
import logging

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logging.warning("SHAP not available, explainability features disabled")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SHAPSupport:
    """SHAP explainability support."""
    
    def __init__(self, inferencer):
        """
        Initialize SHAP support.
        
        Args:
            inferencer: ModelInferencer instance
        """
        self.inferencer = inferencer
        self.explainer = None
        
        if not SHAP_AVAILABLE:
            logger.warning("SHAP library not available")
        else:
            logger.info("SHAP support initialized")
    
    def generate_explanation(self, features: Dict[str, float], 
                           inference_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate SHAP explanation.
        
        Args:
            features: Input features
            inference_result: Inference result
            
        Returns:
            SHAP explanation dictionary
        """
        if not SHAP_AVAILABLE or not self.inferencer.model:
            return {
                "available": False,
                "explanation": "SHAP not available or model not loaded"
            }
        
        try:
            # Prepare feature vector
            feature_names = [
                'process_count', 'high_cpu_processes', 'high_memory_processes',
                'suspicious_process_names', 'file_count', 'suspicious_extensions',
                'suspicious_paths', 'connection_count', 'established_connections',
                'security_event_count', 'audit_log_cleared'
            ]
            
            feature_vector = np.array([[
                features.get(name, 0.0) for name in feature_names
            ]])
            
            # Create explainer if needed
            if self.explainer is None:
                if hasattr(self.inferencer.model, 'predict_proba'):
                    self.explainer = shap.TreeExplainer(self.inferencer.model)
                else:
                    # Fallback for non-tree models
                    return {
                        "available": False,
                        "explanation": "Model type not supported for SHAP"
                    }
            
            # Calculate SHAP values
            shap_values = self.explainer.shap_values(feature_vector)
            
            # Extract values
            if isinstance(shap_values, list):
                shap_vals = shap_values[1] if len(shap_values) > 1 else shap_values[0]
            else:
                shap_vals = shap_values[0]
            
            # Create feature importance dictionary
            feature_importance = {}
            for i, name in enumerate(feature_names):
                feature_importance[name] = float(shap_vals[i])
            
            # Generate explanation text
            sorted_features = sorted(
                feature_importance.items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )
            
            explanation_parts = []
            for feature_name, importance in sorted_features[:3]:
                if abs(importance) > 0.01:
                    direction = "increased" if importance > 0 else "decreased"
                    explanation_parts.append(
                        f"{feature_name} {direction} threat score by {abs(importance):.3f}"
                    )
            
            explanation = "; ".join(explanation_parts) if explanation_parts else "All features have minimal impact"
            
            return {
                "available": True,
                "feature_importance": feature_importance,
                "explanation": explanation,
                "shap_values": shap_vals.tolist() if hasattr(shap_vals, 'tolist') else shap_vals
            }
        
        except Exception as e:
            logger.error(f"SHAP explanation error: {e}")
            return {
                "available": False,
                "error": str(e)
            }

