# Path and File Name : /home/ransomeye/rebuild/ransomeye_hnmp_engine/ml/shap_explainer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: SHAP explainer for risk model predictions

import numpy as np
from typing import Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("SHAP library not available, using simplified explainability")

class SHAPExplainer:
    """
    Generates SHAP explanations for risk model predictions.
    """
    
    def __init__(self, model=None, scaler=None):
        """
        Initialize SHAP explainer.
        
        Args:
            model: Trained risk model
            scaler: Feature scaler
        """
        self.model = model
        self.scaler = scaler
        self.explainer = None
        self.feature_names = [
            'num_failed_high',
            'num_open_ports',
            'kernel_age_days',
            'num_failed_critical',
            'num_packages',
            'num_services'
        ]
    
    def explain(self, host_data: Dict[str, Any], risk_factor: float,
                background_data: Optional[np.ndarray] = None) -> Optional[Dict[str, Any]]:
        """
        Generate SHAP explanation for risk prediction.
        
        Args:
            host_data: Host profile dictionary
            risk_factor: Predicted risk factor
            background_data: Background data for explainer (optional)
            
        Returns:
            SHAP explanation dictionary or None
        """
        if not SHAP_AVAILABLE:
            return self._simple_explanation(host_data, risk_factor)
        
        if self.model is None:
            return self._simple_explanation(host_data, risk_factor)
        
        try:
            # Extract features
            from .risk_model import RiskModel
            risk_model = RiskModel()
            features = risk_model._extract_features(host_data)
            
            # Scale features
            if self.scaler and hasattr(self.scaler, 'mean_'):
                features_scaled = self.scaler.transform(features)
            else:
                features_scaled = features
            
            # Create explainer if not exists
            if self.explainer is None:
                # Use TreeExplainer for RandomForest
                if hasattr(self.model, 'tree_') or hasattr(self.model, 'estimators_'):
                    try:
                        self.explainer = shap.TreeExplainer(self.model)
                    except:
                        # Fallback to KernelExplainer
                        if background_data is None:
                            background_data = np.zeros((10, features_scaled.shape[1]))
                        self.explainer = shap.KernelExplainer(
                            self.model.predict,
                            background_data
                        )
                else:
                    if background_data is None:
                        background_data = np.zeros((10, features_scaled.shape[1]))
                    self.explainer = shap.KernelExplainer(
                        self.model.predict,
                        background_data
                    )
            
            # Calculate SHAP values
            if isinstance(self.explainer, shap.TreeExplainer):
                shap_values = self.explainer.shap_values(features_scaled)
                base_value = self.explainer.expected_value
            else:
                shap_values = self.explainer.shap_values(features_scaled[0])
                base_value = self.explainer.expected_value if hasattr(self.explainer, 'expected_value') else 0.0
            
            # Handle array outputs
            if isinstance(shap_values, list):
                shap_values = shap_values[0] if len(shap_values) > 0 else shap_values
            
            # Flatten if needed
            if shap_values.ndim > 1:
                shap_values = shap_values[0]
            
            # Create explanation dictionary
            shap_dict = {}
            for i, name in enumerate(self.feature_names):
                if i < len(shap_values):
                    shap_dict[name] = float(shap_values[i])
            
            return {
                'shap_values': shap_dict,
                'base_value': float(base_value),
                'risk_factor': float(risk_factor),
                'feature_values': {
                    name: float(features[0][i]) for i, name in enumerate(self.feature_names)
                }
            }
            
        except Exception as e:
            logger.warning(f"SHAP explanation failed: {e}, using simple explanation")
            return self._simple_explanation(host_data, risk_factor)
    
    def _simple_explanation(self, host_data: Dict[str, Any], risk_factor: float) -> Dict[str, Any]:
        """
        Generate simple explanation without SHAP.
        
        Args:
            host_data: Host profile dictionary
            risk_factor: Predicted risk factor
            
        Returns:
            Simple explanation dictionary
        """
        profile = host_data.get('profile', host_data)
        
        num_failed_high = host_data.get('num_failed_high', 0)
        num_failed_critical = host_data.get('num_failed_critical', 0)
        num_open_ports = len(profile.get('open_ports', []))
        kernel_age_days = host_data.get('kernel_age_days', 365)
        
        explanations = []
        
        if num_failed_critical > 0:
            explanations.append(f"{num_failed_critical} critical compliance failures")
        if num_failed_high > 0:
            explanations.append(f"{num_failed_high} high-severity compliance failures")
        if num_open_ports > 10:
            explanations.append(f"{num_open_ports} open ports (high exposure)")
        if kernel_age_days > 365:
            explanations.append(f"Kernel age: {kernel_age_days} days (outdated)")
        
        return {
            'shap_values': {},
            'base_value': 0.0,
            'risk_factor': float(risk_factor),
            'explanations': explanations,
            'feature_values': {
                'num_failed_high': num_failed_high,
                'num_open_ports': num_open_ports,
                'kernel_age_days': kernel_age_days,
                'num_failed_critical': num_failed_critical
            },
            'method': 'simple'
        }

