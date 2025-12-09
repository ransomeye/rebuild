# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/models/shap_support.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: SHAP explainability support for Validator decisions

import os
from typing import Dict, Any, Optional, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import SHAP
try:
    import shap
    import numpy as np
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("SHAP not available. Install: pip install shap")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SHAPSupport:
    """
    SHAP explainability support for model decisions.
    """
    
    def __init__(self, model=None, feature_names: Optional[List[str]] = None):
        """
        Initialize SHAP support.
        
        Args:
            model: Model to explain (optional)
            feature_names: Feature names (optional)
        """
        self.model = model
        self.feature_names = feature_names or []
        self.explainer = None
    
    def create_explainer(self, background_data=None):
        """
        Create SHAP explainer.
        
        Args:
            background_data: Background data for explainer
        """
        if not SHAP_AVAILABLE:
            logger.warning("SHAP not available")
            return
        
        if not self.model:
            logger.warning("No model provided")
            return
        
        try:
            # Use TreeExplainer for tree-based models
            if hasattr(self.model, 'tree_'):
                self.explainer = shap.TreeExplainer(self.model)
            else:
                # Use KernelExplainer as fallback
                if background_data is None:
                    background_data = np.zeros((1, 10))  # Dummy background
                self.explainer = shap.KernelExplainer(self.model.predict_proba, background_data)
            
            logger.info("SHAP explainer created")
        except Exception as e:
            logger.error(f"Error creating SHAP explainer: {e}")
    
    def explain(
        self,
        instance,
        feature_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate SHAP explanation for an instance.
        
        Args:
            instance: Instance to explain
            feature_names: Optional feature names
            
        Returns:
            SHAP explanation dictionary
        """
        if not SHAP_AVAILABLE or not self.explainer:
            return {
                'available': False,
                'error': 'SHAP explainer not available'
            }
        
        try:
            shap_values = self.explainer.shap_values(instance)
            
            # Convert to dictionary
            if isinstance(shap_values, list):
                shap_values = shap_values[1]  # For binary classification, use positive class
            
            feature_names = feature_names or self.feature_names or [f"feature_{i}" for i in range(len(shap_values))]
            
            explanation = {
                'available': True,
                'shap_values': shap_values.tolist() if hasattr(shap_values, 'tolist') else shap_values,
                'feature_names': feature_names,
                'base_value': float(self.explainer.expected_value) if hasattr(self.explainer, 'expected_value') else 0.0
            }
            
            return explanation
            
        except Exception as e:
            logger.error(f"Error generating SHAP explanation: {e}")
            return {
                'available': False,
                'error': str(e)
            }
    
    def explain_validator_decision(
        self,
        answer: str,
        context: str,
        validator_model
    ) -> Dict[str, Any]:
        """
        Explain validator decision using SHAP.
        
        Args:
            answer: Answer text
            context: Context text
            validator_model: Validator model
            
        Returns:
            SHAP explanation
        """
        # Create simple features
        features = np.array([[len(answer), len(context), 0.5]])  # Simplified
        
        self.model = validator_model
        self.create_explainer()
        
        return self.explain(features, ['answer_length', 'context_length', 'similarity'])

