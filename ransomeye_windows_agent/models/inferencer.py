# Path and File Name : /home/ransomeye/rebuild/ransomeye_windows_agent/models/inferencer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Wrapper for local ML model inference using scikit-learn or onnxruntime

import os
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelInferencer:
    """ML model inference wrapper."""
    
    def __init__(self):
        """Initialize model inferencer."""
        self.model = None
        self.model_version = None
        
        # Windows-specific model path
        model_base = os.path.join(
            os.environ.get('PROGRAMDATA', 'C:\\ProgramData'),
            'RansomEye',
            'models'
        )
        
        self.model_path = os.environ.get(
            'MODEL_PATH',
            os.path.join(model_base, 'detector_model.pkl')
        )
        self._load_model()
        logger.info("Model inferencer initialized")
    
    def _load_model(self):
        """Load ML model from disk."""
        try:
            model_file = Path(self.model_path)
            if model_file.exists():
                with open(model_file, 'rb') as f:
                    model_data = pickle.load(f)
                    if isinstance(model_data, dict):
                        self.model = model_data.get('model')
                        self.model_version = model_data.get('version', '1.0.0')
                    else:
                        self.model = model_data
                        self.model_version = '1.0.0'
                logger.info(f"Model loaded: {self.model_path} (version: {self.model_version})")
            else:
                logger.warning(f"Model not found: {self.model_path}, using default")
                self._load_default_model()
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self._load_default_model()
    
    def _load_default_model(self):
        """Load default model (simple threshold-based)."""
        from sklearn.ensemble import RandomForestClassifier
        
        # Create a simple default model
        self.model = RandomForestClassifier(n_estimators=10, random_state=42)
        # Train on dummy data
        X_dummy = np.random.rand(10, 10)
        y_dummy = np.random.randint(0, 2, 10)
        self.model.fit(X_dummy, y_dummy)
        self.model_version = 'default'
        logger.info("Default model loaded")
    
    def predict(self, features: Dict[str, float]) -> Dict[str, Any]:
        """
        Predict threat score from features.
        
        Args:
            features: Feature dictionary
            
        Returns:
            Prediction result with threat_score and explanation
        """
        try:
            # Convert features to array
            feature_names = [
                'process_count', 'high_cpu_processes', 'high_memory_processes',
                'suspicious_process_names', 'file_count', 'suspicious_extensions',
                'suspicious_paths', 'connection_count', 'established_connections',
                'security_event_count', 'audit_log_cleared'
            ]
            
            feature_vector = np.array([[
                features.get(name, 0.0) for name in feature_names
            ]])
            
            # Predict
            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba(feature_vector)[0]
                threat_score = float(proba[1]) if len(proba) > 1 else float(proba[0])
            else:
                prediction = self.model.predict(feature_vector)[0]
                threat_score = 1.0 if prediction == 1 else 0.0
            
            explanation = f"ML model prediction (score: {threat_score:.3f}, version: {self.model_version})"
            
            return {
                "threat_score": threat_score,
                "explanation": explanation,
                "model_version": self.model_version
            }
        
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {
                "threat_score": 0.0,
                "explanation": f"Prediction error: {str(e)}",
                "model_version": self.model_version or "unknown"
            }

