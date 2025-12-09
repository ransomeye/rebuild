# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/llm_core/confidence_estimator.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Trainable regression model that predicts accuracy score based on prompt/output features

import os
import pickle
from pathlib import Path
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import ML libraries
try:
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available. Install: pip install scikit-learn")

# Try to import SHAP
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("SHAP not available. Install: pip install shap")


class ConfidenceEstimator:
    """
    Trainable confidence estimator that predicts accuracy score.
    Uses regression model with SHAP explainability.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize confidence estimator.
        
        Args:
            model_path: Path to trained model file
        """
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.model_path = model_path
        
        if model_path:
            self.load_model(model_path)
        else:
            self._init_default_model()
    
    def _init_default_model(self):
        """Initialize default heuristic model."""
        logger.info("Initializing default heuristic confidence estimator")
        self.model = None
        self.scaler = None
        self.feature_names = [
            'prompt_length', 'output_length', 'prompt_entropy', 'output_entropy',
            'context_length', 'num_context_chunks', 'avg_context_score',
            'has_numbers', 'has_dates', 'coherence_score'
        ]
    
    def load_model(self, model_path: str):
        """Load trained model."""
        model_file = Path(model_path)
        if not model_file.exists():
            logger.error(f"Model file not found: {model_path}")
            return
        
        try:
            with open(model_file, 'rb') as f:
                model_data = pickle.load(f)
            
            if isinstance(model_data, dict):
                self.model = model_data.get('model')
                self.scaler = model_data.get('scaler')
                self.feature_names = model_data.get('feature_names', self.feature_names)
            else:
                self.model = model_data
            
            self.model_path = model_path
            logger.info(f"Loaded confidence model from {model_path}")
        
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self._init_default_model()
    
    def extract_features(
        self,
        prompt: str,
        output: str,
        context: Optional[Dict] = None
    ) -> List[float]:
        """
        Extract features from prompt, output, and context.
        
        Args:
            prompt: Input prompt
            output: LLM output
            context: Optional context metadata
            
        Returns:
            Feature vector
        """
        features = []
        
        # Prompt features
        features.append(len(prompt))
        features.append(self._calculate_entropy(prompt))
        
        # Output features
        features.append(len(output))
        features.append(self._calculate_entropy(output))
        
        # Context features
        if context:
            features.append(context.get('total_length', 0))
            features.append(context.get('num_chunks', 0))
            avg_score = sum(c.get('score', 0) for c in context.get('chunks', [])) / max(len(context.get('chunks', [])), 1)
            features.append(avg_score)
        else:
            features.extend([0, 0, 0])
        
        # Content features
        features.append(1.0 if any(c.isdigit() for c in output) else 0.0)
        features.append(1.0 if any(word in output.lower() for word in ['date', 'time', '2024', '2023']) else 0.0)
        
        # Coherence score (simple heuristic)
        coherence = self._calculate_coherence(output)
        features.append(coherence)
        
        return features
    
    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy."""
        if not text:
            return 0.0
        
        import math
        char_counts = {}
        for char in text:
            char_counts[char] = char_counts.get(char, 0) + 1
        
        entropy = 0.0
        text_len = len(text)
        for count in char_counts.values():
            prob = count / text_len
            entropy -= prob * math.log2(prob)
        
        return entropy
    
    def _calculate_coherence(self, text: str) -> float:
        """Calculate simple coherence score."""
        if not text:
            return 0.0
        
        # Simple heuristic: sentence length consistency
        sentences = text.split('.')
        if len(sentences) < 2:
            return 0.5
        
        lengths = [len(s) for s in sentences]
        avg_length = sum(lengths) / len(lengths)
        variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
        
        # Lower variance = higher coherence
        coherence = 1.0 / (1.0 + variance / 100.0)
        return min(1.0, coherence)
    
    def estimate(
        self,
        prompt: str,
        output: str,
        context: Optional[Dict] = None,
        return_shap: bool = True
    ) -> Dict:
        """
        Estimate confidence score for output.
        
        Args:
            prompt: Input prompt
            output: LLM output
            context: Optional context metadata
            return_shap: Whether to compute SHAP values
            
        Returns:
            Dictionary with confidence score and SHAP values
        """
        # Extract features
        features = self.extract_features(prompt, output, context)
        
        # Use ML model if available
        if self.model is not None and SKLEARN_AVAILABLE:
            if SKLEARN_AVAILABLE:
                import numpy as np
                features_array = np.array(features).reshape(1, -1)
                
                # Scale if scaler available
                if self.scaler is not None:
                    features_array = self.scaler.transform(features_array)
                
                # Predict
                confidence_score = float(self.model.predict(features_array)[0])
                confidence_score = max(0.0, min(1.0, confidence_score))  # Clamp to [0, 1]
                
                # Compute SHAP if requested
                shap_values = None
                if return_shap and SHAP_AVAILABLE:
                    shap_values = self._compute_shap(features_array)
            else:
                confidence_score = self._heuristic_confidence(features)
                shap_values = None
        else:
            # Use heuristic
            confidence_score = self._heuristic_confidence(features)
            shap_values = self._heuristic_shap(features) if return_shap else None
        
        return {
            'confidence_score': confidence_score,
            'features': dict(zip(self.feature_names, features)),
            'shap_values': shap_values
        }
    
    def _heuristic_confidence(self, features: List[float]) -> float:
        """Compute heuristic confidence score."""
        # Simple heuristic based on features
        score = 0.5  # Base score
        
        # Longer outputs tend to be more confident (up to a point)
        output_length = features[2]
        if 100 <= output_length <= 1000:
            score += 0.2
        
        # Higher coherence = higher confidence
        coherence = features[-1]
        score += coherence * 0.3
        
        return min(1.0, max(0.0, score))
    
    def _heuristic_shap(self, features: List[float]) -> Dict:
        """Compute heuristic SHAP values."""
        shap_dict = {}
        for i, (name, value) in enumerate(zip(self.feature_names, features)):
            contribution = 0.0
            
            if name == 'coherence_score':
                contribution = value * 0.3
            elif name == 'output_length' and 100 <= value <= 1000:
                contribution = 0.2
            
            shap_dict[name] = {
                'value': value,
                'contribution': contribution
            }
        
        return shap_dict
    
    def _compute_shap(self, features_array) -> Optional[Dict]:
        """Compute SHAP values using SHAP library."""
        if not SHAP_AVAILABLE or self.model is None:
            return None
        
        try:
            if hasattr(self.model, 'tree_'):
                explainer = shap.TreeExplainer(self.model)
                shap_values = explainer.shap_values(features_array)
                
                if isinstance(shap_values, list):
                    shap_values = shap_values[0]
                
                shap_dict = {}
                for i, name in enumerate(self.feature_names):
                    shap_dict[name] = {
                        'value': float(features_array[0][i]),
                        'contribution': float(shap_values[0][i])
                    }
                
                return shap_dict
        except Exception as e:
            logger.error(f"Error computing SHAP: {e}")
            return None

