# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/trust/trust_score.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: ML Model wrapper for trust scoring with SHAP explainability. Inputs: source_reputation, age, sightings_count. Output: trust_score (0-1)

import os
import sys
import pickle
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Try to import ML and SHAP
try:
    import numpy as np
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("SHAP not available. Install: pip install shap")

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrustScorer:
    """
    ML-based trust scoring for IOCs.
    Inputs: source_reputation, age, sightings_count
    Output: trust_score (0-1) with SHAP explanation
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize trust scorer.
        
        Args:
            model_path: Path to trained model
        """
        self.model_path = model_path or os.environ.get('TRUST_MODEL_PATH')
        self.model = None
        self.explainer = None
        self._load_model()
    
    def _load_model(self):
        """Load trained model."""
        if self.model_path and os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    if isinstance(model_data, dict):
                        self.model = model_data.get('model')
                    else:
                        self.model = model_data
                logger.info(f"Loaded trust model from {self.model_path}")
            except Exception as e:
                logger.warning(f"Could not load trust model: {e}")
    
    def score(
        self,
        source_reputation: float,
        age_days: float,
        sightings_count: int,
        additional_features: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate trust score for IOC.
        
        Args:
            source_reputation: Source reputation score (0-1)
            age_days: Age of IOC in days
            sightings_count: Number of sightings
            additional_features: Optional additional features
            
        Returns:
            Dictionary with trust_score and SHAP explanation
        """
        # Prepare features
        features = np.array([[
            source_reputation,
            age_days,
            float(sightings_count)
        ]])
        
        # Add additional features if provided
        if additional_features:
            # Extend feature vector
            pass  # Can be extended
        
        # Calculate trust score
        if self.model:
            try:
                if hasattr(self.model, 'predict_proba'):
                    proba = self.model.predict_proba(features)[0]
                    trust_score = float(proba[1])  # Probability of high trust
                elif hasattr(self.model, 'predict'):
                    prediction = self.model.predict(features)[0]
                    trust_score = float(prediction) if isinstance(prediction, (int, float)) else 0.5
                else:
                    trust_score = 0.5
            except Exception as e:
                logger.error(f"Error in model prediction: {e}")
                trust_score = self._rule_based_score(source_reputation, age_days, sightings_count)
        else:
            trust_score = self._rule_based_score(source_reputation, age_days, sightings_count)
        
        # Generate SHAP explanation
        shap_explanation = None
        if SHAP_AVAILABLE and self.model and self.explainer:
            try:
                shap_values = self.explainer.shap_values(features)
                shap_explanation = {
                    'source_reputation': float(shap_values[0][0]) if isinstance(shap_values, list) else float(shap_values[0][0]),
                    'age_days': float(shap_values[0][1]) if isinstance(shap_values, list) else float(shap_values[0][1]),
                    'sightings_count': float(shap_values[0][2]) if isinstance(shap_values, list) else float(shap_values[0][2])
                }
            except Exception as e:
                logger.warning(f"Error generating SHAP explanation: {e}")
        
        return {
            'trust_score': float(trust_score),
            'shap_explanation': shap_explanation,
            'features': {
                'source_reputation': source_reputation,
                'age_days': age_days,
                'sightings_count': sightings_count
            }
        }
    
    def _rule_based_score(
        self,
        source_reputation: float,
        age_days: float,
        sightings_count: int
    ) -> float:
        """
        Rule-based trust score fallback.
        
        Args:
            source_reputation: Source reputation
            age_days: Age in days
            sightings_count: Sightings count
            
        Returns:
            Trust score (0-1)
        """
        # Weighted combination
        score = (source_reputation * 0.5) + (min(age_days / 365.0, 1.0) * 0.2) + (min(sightings_count / 100.0, 1.0) * 0.3)
        return max(0.0, min(1.0, score))
    
    def create_explainer(self, background_data: Optional[np.ndarray] = None):
        """
        Create SHAP explainer.
        
        Args:
            background_data: Background data for explainer
        """
        if not SHAP_AVAILABLE or not self.model:
            return
        
        try:
            if background_data is None:
                # Create dummy background
                background_data = np.array([[0.5, 30.0, 10.0]])
            
            if hasattr(self.model, 'tree_'):
                self.explainer = shap.TreeExplainer(self.model)
            else:
                self.explainer = shap.KernelExplainer(self.model.predict_proba, background_data)
            
            logger.info("Created SHAP explainer")
        except Exception as e:
            logger.warning(f"Could not create SHAP explainer: {e}")

