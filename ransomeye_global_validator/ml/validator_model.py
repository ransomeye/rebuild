# Path and File Name : /home/ransomeye/rebuild/ransomeye_global_validator/ml/validator_model.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Trainable RandomForest classifier to score validation run health based on latency and error rates

import os
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidatorModel:
    """Trainable ML model for validation run health scoring."""
    
    def __init__(self):
        """Initialize validator model."""
        self.model = None
        self.scaler = StandardScaler()
        self.model_path = os.environ.get(
            'VALIDATOR_MODEL_PATH',
            '/home/ransomeye/rebuild/ransomeye_global_validator/ml/models/validator_model.pkl'
        )
        self.feature_names = [
            'api_latency_avg',
            'api_latency_max',
            'error_count',
            'queue_depth',
            'total_steps',
            'success_rate'
        ]
        self._load_model()
        logger.info("Validator model initialized")
    
    def _load_model(self):
        """Load trained model from disk."""
        try:
            model_file = Path(self.model_path)
            if model_file.exists():
                with open(model_file, 'rb') as f:
                    model_data = pickle.load(f)
                    self.model = model_data.get('model')
                    self.scaler = model_data.get('scaler', StandardScaler())
                logger.info(f"Model loaded from {self.model_path}")
            else:
                # Initialize with default model if not trained yet
                self.model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    n_jobs=-1
                )
                logger.info("Using default untrained model")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            # Fallback to default model
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
    
    def predict_health(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        Predict health score for validation run.
        
        Args:
            metrics: Dictionary of metrics (api_latency_avg, error_count, etc.)
            
        Returns:
            Prediction result with health_score and is_healthy
        """
        if not self.model:
            # Default prediction if model not available
            return {
                "health_score": 0.5,
                "is_healthy": True,
                "explanation": "Model not trained, using default prediction"
            }
        
        try:
            # Extract features in correct order
            feature_vector = np.array([[
                metrics.get('api_latency_avg', 0.0),
                metrics.get('api_latency_max', 0.0),
                metrics.get('error_count', 0.0),
                metrics.get('queue_depth', 0.0),
                metrics.get('total_steps', 0.0),
                metrics.get('success_rate', 1.0)
            ]])
            
            # Scale features
            feature_vector_scaled = self.scaler.transform(feature_vector)
            
            # Predict probability
            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba(feature_vector_scaled)[0]
                health_score = float(proba[1]) if len(proba) > 1 else float(proba[0])
            else:
                # Fallback for models without predict_proba
                prediction = self.model.predict(feature_vector_scaled)[0]
                health_score = 1.0 if prediction == 1 else 0.0
            
            is_healthy = health_score >= 0.7  # Threshold for healthy
            
            explanation = self._generate_explanation(metrics, health_score, is_healthy)
            
            return {
                "health_score": health_score,
                "is_healthy": is_healthy,
                "explanation": explanation,
                "metrics": metrics
            }
        
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {
                "health_score": 0.0,
                "is_healthy": False,
                "explanation": f"Prediction error: {str(e)}",
                "error": str(e)
            }
    
    def _generate_explanation(self, metrics: Dict[str, float], 
                             health_score: float, is_healthy: bool) -> str:
        """
        Generate human-readable explanation for prediction.
        
        Args:
            metrics: Input metrics
            health_score: Predicted health score
            is_healthy: Whether run is considered healthy
            
        Returns:
            Explanation string
        """
        explanations = []
        
        if metrics.get('api_latency_avg', 0) > 500:
            explanations.append("High API latency detected (>500ms)")
        
        if metrics.get('error_count', 0) > 0:
            explanations.append(f"{int(metrics['error_count'])} errors encountered")
        
        if metrics.get('success_rate', 1.0) < 0.8:
            explanations.append(f"Low success rate ({metrics['success_rate']*100:.1f}%)")
        
        if not explanations:
            explanations.append("All metrics within acceptable ranges")
        
        status = "healthy" if is_healthy else "unhealthy"
        return f"Run is {status} (score: {health_score:.2f}). {'. '.join(explanations)}."
    
    def save_model(self, output_path: Optional[str] = None):
        """
        Save trained model to disk.
        
        Args:
            output_path: Optional custom output path
        """
        path = output_path or self.model_path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names
        }
        
        with open(path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Model saved to {path}")

