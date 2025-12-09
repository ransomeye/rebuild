# Path and File Name : /home/ransomeye/rebuild/ransomeye_global_validator/ml/shap_support.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Generates SHAP plots and values for validator model explainability

import os
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logging.warning("SHAP not available, explainability features disabled")

from .validator_model import ValidatorModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SHAPSupport:
    """SHAP explainability support for validator model."""
    
    def __init__(self, validator_model: ValidatorModel):
        """
        Initialize SHAP support.
        
        Args:
            validator_model: Validator model instance
        """
        self.validator_model = validator_model
        self.explainer = None
        self.shap_output_dir = os.environ.get(
            'SHAP_OUTPUT_DIR',
            '/home/ransomeye/rebuild/ransomeye_global_validator/ml/shap_outputs'
        )
        Path(self.shap_output_dir).mkdir(parents=True, exist_ok=True)
        
        if not SHAP_AVAILABLE:
            logger.warning("SHAP library not available")
        else:
            logger.info("SHAP support initialized")
    
    def generate_explanation(self, metrics: Dict[str, float], 
                           run_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate SHAP explanation for a validation run.
        
        Args:
            metrics: Input metrics
            run_id: Optional run ID for file naming
            
        Returns:
            SHAP explanation data
        """
        if not SHAP_AVAILABLE or not self.validator_model.model:
            return {
                "available": False,
                "explanation": "SHAP not available or model not loaded"
            }
        
        try:
            # Prepare feature vector
            feature_vector = np.array([[
                metrics.get('api_latency_avg', 0.0),
                metrics.get('api_latency_max', 0.0),
                metrics.get('error_count', 0.0),
                metrics.get('queue_depth', 0.0),
                metrics.get('total_steps', 0.0),
                metrics.get('success_rate', 1.0)
            ]])
            
            # Scale features
            feature_vector_scaled = self.validator_model.scaler.transform(feature_vector)
            
            # Create explainer if not exists
            if self.explainer is None:
                # Use TreeExplainer for RandomForest
                self.explainer = shap.TreeExplainer(self.validator_model.model)
            
            # Calculate SHAP values
            shap_values = self.explainer.shap_values(feature_vector_scaled)
            
            # Get feature importance
            feature_importance = {}
            if isinstance(shap_values, list):
                # Binary classification: use positive class
                shap_vals = shap_values[1] if len(shap_values) > 1 else shap_values[0]
            else:
                shap_vals = shap_values[0]
            
            for i, feature_name in enumerate(self.validator_model.feature_names):
                feature_importance[feature_name] = float(shap_vals[i])
            
            # Generate explanation text
            explanation_parts = []
            sorted_features = sorted(
                feature_importance.items(), 
                key=lambda x: abs(x[1]), 
                reverse=True
            )
            
            for feature_name, importance in sorted_features[:3]:
                if abs(importance) > 0.01:
                    direction = "increased" if importance > 0 else "decreased"
                    explanation_parts.append(
                        f"{feature_name} {direction} health score by {abs(importance):.3f}"
                    )
            
            explanation = "Run health influenced by: " + "; ".join(explanation_parts) if explanation_parts else "All features have minimal impact"
            
            result = {
                "available": True,
                "feature_importance": feature_importance,
                "explanation": explanation,
                "shap_values": shap_vals.tolist() if hasattr(shap_vals, 'tolist') else shap_vals
            }
            
            # Save to file if run_id provided
            if run_id:
                output_file = Path(self.shap_output_dir) / f"shap_{run_id}.json"
                import json
                with open(output_file, 'w') as f:
                    json.dump(result, f, indent=2)
                result["output_file"] = str(output_file)
            
            return result
        
        except Exception as e:
            logger.error(f"SHAP explanation error: {e}")
            return {
                "available": False,
                "error": str(e)
            }

