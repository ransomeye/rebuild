# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/training/train_confidence.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Training script for confidence estimator model

import os
import pickle
import json
from pathlib import Path
from typing import List, Dict
import logging

from ..llm_core.confidence_estimator import ConfidenceEstimator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import ML libraries
try:
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error, mean_absolute_error
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class ConfidenceTrainer:
    """
    Trainer for confidence estimator model.
    """
    
    def __init__(self, model_output_dir: str = None):
        """Initialize trainer."""
        if model_output_dir is None:
            model_output_dir = os.environ.get(
                'MODEL_DIR',
                '/home/ransomeye/rebuild/ransomeye_llm_behavior/models'
            )
        
        self.model_output_dir = Path(model_output_dir)
        self.model_output_dir.mkdir(parents=True, exist_ok=True)
        
        self.estimator = ConfidenceEstimator()
    
    def load_training_data(self, data_path: str) -> List[Dict]:
        """Load training data from JSON file."""
        with open(data_path, 'r') as f:
            return json.load(f)
    
    def train(self, training_data: List[Dict], test_size: float = 0.2) -> Dict:
        """
        Train confidence estimator.
        
        Args:
            training_data: List of dicts with 'prompt', 'output', 'context', 'actual_confidence'
            test_size: Fraction for testing
            
        Returns:
            Training results
        """
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn not available")
        
        # Extract features
        X = []
        y = []
        
        for item in training_data:
            features = self.estimator.extract_features(
                prompt=item['prompt'],
                output=item['output'],
                context=item.get('context')
            )
            X.append(features)
            y.append(item['actual_confidence'])
        
        X = np.array(X)
        y = np.array(y)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
        
        # Train model
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_train_pred = model.predict(X_train_scaled)
        y_test_pred = model.predict(X_test_scaled)
        
        train_mse = mean_squared_error(y_train, y_train_pred)
        test_mse = mean_squared_error(y_test, y_test_pred)
        test_mae = mean_absolute_error(y_test, y_test_pred)
        
        # Save model
        self.estimator.model = model
        self.estimator.scaler = scaler
        
        results = {
            'train_mse': float(train_mse),
            'test_mse': float(test_mse),
            'test_mae': float(test_mae),
            'feature_importance': {
                name: float(imp) for name, imp in zip(self.estimator.feature_names, model.feature_importances_)
            }
        }
        
        logger.info(f"Training completed. Test MSE: {test_mse:.4f}, MAE: {test_mae:.4f}")
        return results
    
    def save_model(self, model_id: str) -> str:
        """Save trained model."""
        model_data = {
            'model': self.estimator.model,
            'scaler': self.estimator.scaler,
            'feature_names': self.estimator.feature_names
        }
        
        model_file = self.model_output_dir / f"confidence_{model_id}.pkl"
        with open(model_file, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Saved confidence model to {model_file}")
        return str(model_file)

