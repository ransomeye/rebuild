# Path and File Name : /home/ransomeye/rebuild/ransomeye_dpi_probe/ml/shap_support.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: SHAP explainability generator for ML flow classification

import json
import logging
import numpy as np
from typing import Dict, Any, Optional
import shap

logger = logging.getLogger(__name__)


class SHAPExplainer:
    """SHAP explainability wrapper for flow classifier."""
    
    def __init__(self, model, feature_names: list):
        """
        Initialize SHAP explainer.
        
        Args:
            model: Trained ML model (sklearn-compatible)
            feature_names: List of feature names
        """
        self.model = model
        self.feature_names = feature_names
        
        # Use TreeExplainer for tree-based models, otherwise KernelExplainer
        try:
            if hasattr(model, 'predict_proba'):
                # Try TreeExplainer first (faster)
                self.explainer = shap.TreeExplainer(model)
                self.explainer_type = 'tree'
            else:
                # Fallback to KernelExplainer
                self.explainer = None
                self.explainer_type = 'kernel'
        except Exception as e:
            logger.warning(f"Could not initialize TreeExplainer: {e}, using KernelExplainer")
            self.explainer = None
            self.explainer_type = 'kernel'
    
    def explain(self, X: np.ndarray, background_data: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        Generate SHAP explanation for prediction.
        
        Args:
            X: Feature vector (single sample)
            background_data: Background dataset for KernelExplainer (optional)
            
        Returns:
            Dictionary with SHAP values and explanation
        """
        try:
            # Ensure X is 2D
            if X.ndim == 1:
                X = X.reshape(1, -1)
            
            if self.explainer_type == 'tree' and self.explainer is not None:
                shap_values = self.explainer.shap_values(X)
                
                # Handle multi-class models
                if isinstance(shap_values, list):
                    shap_values = shap_values[1]  # Use positive class
                
                shap_values = shap_values[0]  # Get single sample
            else:
                # Use KernelExplainer
                if background_data is None:
                    # Create minimal background (mean)
                    background_data = np.mean(X, axis=0).reshape(1, -1)
                
                if self.explainer is None:
                    # Initialize KernelExplainer
                    self.explainer = shap.KernelExplainer(
                        self.model.predict_proba if hasattr(self.model, 'predict_proba') else self.model.predict,
                        background_data
                    )
                
                shap_values = self.explainer.shap_values(X[0])
                
                # Handle multi-class
                if isinstance(shap_values, list):
                    shap_values = shap_values[1]
            
            # Get prediction
            if hasattr(self.model, 'predict_proba'):
                prediction_proba = self.model.predict_proba(X)[0]
                prediction = self.model.predict(X)[0]
            else:
                prediction = self.model.predict(X)[0]
                prediction_proba = None
            
            # Build feature contributions
            feature_contributions = {}
            for i, feature_name in enumerate(self.feature_names):
                feature_contributions[feature_name] = {
                    'shap_value': float(shap_values[i]),
                    'contribution': 'positive' if shap_values[i] > 0 else 'negative'
                }
            
            explanation = {
                'prediction': int(prediction) if isinstance(prediction, (np.integer, np.int64)) else prediction,
                'prediction_proba': [float(p) for p in prediction_proba] if prediction_proba is not None else None,
                'feature_contributions': feature_contributions,
                'shap_values': [float(v) for v in shap_values],
                'base_value': float(self.explainer.expected_value) if hasattr(self.explainer, 'expected_value') else 0.0,
                'explainer_type': self.explainer_type
            }
            
            return explanation
            
        except Exception as e:
            logger.error(f"Error generating SHAP explanation: {e}")
            return {
                'error': str(e),
                'prediction': None,
                'feature_contributions': {}
            }
    
    def explain_to_json(self, X: np.ndarray, background_data: Optional[np.ndarray] = None) -> str:
        """
        Generate SHAP explanation as JSON string.
        
        Args:
            X: Feature vector
            background_data: Background dataset (optional)
            
        Returns:
            JSON string
        """
        explanation = self.explain(X, background_data)
        return json.dumps(explanation, indent=2)
    
    def get_feature_importance(self, X: np.ndarray, top_n: int = 10) -> Dict[str, Any]:
        """
        Get top N most important features.
        
        Args:
            X: Feature vector
            top_n: Number of top features to return
            
        Returns:
            Dictionary with top features
        """
        explanation = self.explain(X)
        
        if 'error' in explanation:
            return explanation
        
        # Sort by absolute SHAP value
        features = explanation['feature_contributions'].items()
        sorted_features = sorted(features, key=lambda x: abs(x[1]['shap_value']), reverse=True)
        
        top_features = {}
        for feature_name, contrib in sorted_features[:top_n]:
            top_features[feature_name] = contrib
        
        return {
            'top_features': top_features,
            'prediction': explanation['prediction'],
            'base_value': explanation['base_value']
        }

