# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/ml/inference/classifier.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: ML classifier that takes DNA features and outputs malicious score with SHAP explainability

import os
import pickle
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

# Try to import numpy
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("numpy not available. Some functionality may be limited.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import ML libraries
try:
    from sklearn.ensemble import RandomForestClassifier
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


class ForensicClassifier:
    """
    ML classifier for forensic artifacts.
    Takes DNA features and outputs malicious probability with SHAP explainability.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize classifier.
        
        Args:
            model_path: Path to trained model file (.pkl)
        """
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.model_path = model_path
        
        if model_path:
            self.load_model(model_path)
        else:
            # Initialize with default heuristic model if no model provided
            self._init_default_model()
    
    def _init_default_model(self):
        """Initialize default heuristic-based model if ML libraries unavailable."""
        logger.info("Initializing default heuristic classifier")
        self.model = None
        self.scaler = None
        self.feature_names = [
            'entropy_overall', 'entropy_max', 'high_entropy_percentage',
            'suspicious_strings_count', 'imports_count', 'yara_matches_count',
            'file_size', 'is_packed', 'is_executable'
        ]
    
    def load_model(self, model_path: str):
        """
        Load trained model from file.
        
        Args:
            model_path: Path to model file
        """
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
            logger.info(f"Loaded model from {model_path}")
        
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self._init_default_model()
    
    def extract_features(self, dna_data: Dict):
        """
        Extract feature vector from DNA data.
        
        Args:
            dna_data: DNA feature dictionary
            
        Returns:
            Feature vector as numpy array
        """
        features = []
        
        # Entropy features
        entropy_data = dna_data.get('entropy', {})
        features.append(entropy_data.get('overall', 0.0))
        features.append(entropy_data.get('max', 0.0))
        features.append(entropy_data.get('high_entropy_percentage', 0.0))
        
        # String features
        strings_data = dna_data.get('strings', {})
        features.append(strings_data.get('suspicious_count', 0))
        
        # Import features
        imports = dna_data.get('imports', [])
        features.append(len(imports))
        
        # YARA matches
        yara_matches = dna_data.get('yara_matches', [])
        features.append(len(yara_matches))
        
        # Metadata features
        metadata = dna_data.get('metadata', {})
        features.append(metadata.get('size', 0) / (1024 * 1024))  # Size in MB
        features.append(1.0 if metadata.get('is_packed', False) else 0.0)
        features.append(1.0 if metadata.get('is_executable', False) else 0.0)
        
        if NUMPY_AVAILABLE:
            return np.array(features, dtype=np.float32)
        else:
            return features  # Return as list if numpy unavailable
    
    def predict(self, dna_data: Dict, return_shap: bool = True) -> Dict:
        """
        Predict malicious probability for DNA data.
        
        Args:
            dna_data: DNA feature dictionary
            return_shap: Whether to compute SHAP explainability
            
        Returns:
            Dictionary with prediction and SHAP values
        """
        # Extract features
        features = self.extract_features(dna_data)
        
        # Convert to numpy array if needed
        if not NUMPY_AVAILABLE and isinstance(features, list):
            # Cannot use ML model without numpy
            malicious_score = self._heuristic_score(features, dna_data)
            shap_values = self._heuristic_shap(features, dna_data) if return_shap else None
            return {
                'is_malicious': malicious_score > 0.5,
                'malicious_score': float(malicious_score),
                'confidence': abs(malicious_score - 0.5) * 2,
                'shap_values': shap_values,
                'features_used': self.feature_names or []
            }
        
        # Use ML model if available
        if self.model is not None and SKLEARN_AVAILABLE and NUMPY_AVAILABLE:
            # Scale features if scaler available
            if self.scaler is not None:
                features_scaled = self.scaler.transform(features.reshape(1, -1))
            else:
                features_scaled = features.reshape(1, -1)
            
            # Predict
            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba(features_scaled)[0]
                malicious_score = proba[1] if len(proba) > 1 else proba[0]
            else:
                prediction = self.model.predict(features_scaled)[0]
                malicious_score = float(prediction)
            
            # Compute SHAP if requested
            shap_values = None
            if return_shap and SHAP_AVAILABLE:
                shap_values = self._compute_shap(features_scaled)
        
        else:
            # Use heuristic model
            malicious_score = self._heuristic_score(features, dna_data)
            shap_values = self._heuristic_shap(features, dna_data) if return_shap else None
        
        return {
            'is_malicious': malicious_score > 0.5,
            'malicious_score': float(malicious_score),
            'confidence': abs(malicious_score - 0.5) * 2,  # Distance from 0.5
            'shap_values': shap_values,
            'features_used': self.feature_names or []
        }
    
    def _heuristic_score(self, features, dna_data: Dict) -> float:
        """
        Compute heuristic malicious score.
        
        Args:
            features: Feature vector
            dna_data: DNA data
            
        Returns:
            Malicious score (0-1)
        """
        score = 0.0
        
        # High entropy (packed/encrypted)
        if features[2] > 50:  # high_entropy_percentage
            score += 0.3
        
        # Suspicious strings
        if features[3] > 5:  # suspicious_strings_count
            score += 0.2
        
        # YARA matches
        if features[5] > 0:  # yara_matches_count
            score += 0.3
        
        # Packed
        if features[7] > 0.5:  # is_packed
            score += 0.2
        
        # Normalize to 0-1
        return min(1.0, score)
    
    def _heuristic_shap(self, features, dna_data: Dict) -> Dict:
        """
        Compute heuristic SHAP values.
        
        Args:
            features: Feature vector
            dna_data: DNA data
            
        Returns:
            SHAP values dictionary
        """
        shap_dict = {}
        
        feature_names = self.feature_names or [f'feature_{i}' for i in range(len(features))]
        
        for i, (name, value) in enumerate(zip(feature_names, features)):
            contribution = 0.0
            
            if name == 'high_entropy_percentage' and value > 50:
                contribution = 0.3
            elif name == 'suspicious_strings_count' and value > 5:
                contribution = 0.2
            elif name == 'yara_matches_count' and value > 0:
                contribution = 0.3
            elif name == 'is_packed' and value > 0.5:
                contribution = 0.2
            
            shap_dict[name] = {
                'value': float(value),
                'contribution': contribution,
                'base_value': 0.0
            }
        
        return shap_dict
    
    def _compute_shap(self, features: np.ndarray) -> Optional[Dict]:
        """
        Compute SHAP values using SHAP library.
        
        Args:
            features: Scaled feature vector
            
        Returns:
            SHAP values dictionary or None
        """
        if not SHAP_AVAILABLE or self.model is None:
            return None
        
        try:
            # Use TreeExplainer for tree-based models
            if hasattr(self.model, 'tree_'):
                explainer = shap.TreeExplainer(self.model)
                shap_values = explainer.shap_values(features)
                
                # Convert to dictionary
                if isinstance(shap_values, list):
                    shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]
                
                shap_dict = {}
                feature_names = self.feature_names or [f'feature_{i}' for i in range(len(features[0]))]
                
                for i, name in enumerate(feature_names):
                    shap_dict[name] = {
                        'value': float(features[0][i]),
                        'contribution': float(shap_values[0][i]),
                        'base_value': float(explainer.expected_value[1] if isinstance(explainer.expected_value, np.ndarray) else explainer.expected_value)
                    }
                
                return shap_dict
            
            else:
                # Use KernelExplainer for other models (slower)
                explainer = shap.KernelExplainer(self.model.predict_proba, features)
                shap_values = explainer.shap_values(features, nsamples=100)
                
                shap_dict = {}
                feature_names = self.feature_names or [f'feature_{i}' for i in range(len(features[0]))]
                
                for i, name in enumerate(feature_names):
                    shap_dict[name] = {
                        'value': float(features[0][i]),
                        'contribution': float(shap_values[1][0][i] if isinstance(shap_values, list) else shap_values[0][i]),
                        'base_value': float(explainer.expected_value[1] if isinstance(explainer.expected_value, np.ndarray) else explainer.expected_value)
                    }
                
                return shap_dict
        
        except Exception as e:
            logger.error(f"Error computing SHAP values: {e}")
            return None

