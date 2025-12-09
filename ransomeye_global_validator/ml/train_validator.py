# Path and File Name : /home/ransomeye/rebuild/ransomeye_global_validator/ml/train_validator.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Training script for validator model using historical validation run data

import os
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import logging

from .validator_model import ValidatorModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidatorTrainer:
    """Trains the validator model on historical data."""
    
    def __init__(self):
        """Initialize trainer."""
        self.validator_model = ValidatorModel()
        self.training_data_path = os.environ.get(
            'VALIDATOR_TRAINING_DATA_PATH',
            '/home/ransomeye/rebuild/ransomeye_global_validator/ml/training_data.jsonl'
        )
        logger.info("Validator trainer initialized")
    
    def load_training_data(self) -> tuple:
        """
        Load training data from JSONL file.
        
        Returns:
            Tuple of (features, labels)
        """
        features = []
        labels = []
        
        data_path = Path(self.training_data_path)
        if not data_path.exists():
            logger.warning(f"Training data not found at {self.training_data_path}, generating synthetic data")
            return self._generate_synthetic_training_data()
        
        try:
            with open(data_path, 'r') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        metrics = data.get('metrics', {})
                        is_healthy = data.get('is_healthy', True)
                        
                        feature_vector = [
                            metrics.get('api_latency_avg', 0.0),
                            metrics.get('api_latency_max', 0.0),
                            metrics.get('error_count', 0.0),
                            metrics.get('queue_depth', 0.0),
                            metrics.get('total_steps', 0.0),
                            metrics.get('success_rate', 1.0)
                        ]
                        
                        features.append(feature_vector)
                        labels.append(1 if is_healthy else 0)
            
            logger.info(f"Loaded {len(features)} training samples")
            return np.array(features), np.array(labels)
        
        except Exception as e:
            logger.error(f"Error loading training data: {e}")
            return self._generate_synthetic_training_data()
    
    def _generate_synthetic_training_data(self) -> tuple:
        """
        Generate synthetic training data for initial model.
        
        Returns:
            Tuple of (features, labels)
        """
        np.random.seed(42)
        n_samples = 1000
        
        features = []
        labels = []
        
        for _ in range(n_samples):
            # Healthy runs: low latency, no errors
            if np.random.random() > 0.3:
                api_latency_avg = np.random.uniform(10, 200)
                api_latency_max = api_latency_avg + np.random.uniform(0, 100)
                error_count = 0.0
                queue_depth = np.random.uniform(0, 5)
                total_steps = np.random.uniform(3, 5)
                success_rate = 1.0
                is_healthy = True
            else:
                # Unhealthy runs: high latency or errors
                api_latency_avg = np.random.uniform(300, 2000)
                api_latency_max = api_latency_avg + np.random.uniform(100, 500)
                error_count = np.random.uniform(1, 5)
                queue_depth = np.random.uniform(10, 50)
                total_steps = np.random.uniform(3, 5)
                success_rate = np.random.uniform(0.3, 0.7)
                is_healthy = False
            
            feature_vector = [
                api_latency_avg,
                api_latency_max,
                error_count,
                queue_depth,
                total_steps,
                success_rate
            ]
            
            features.append(feature_vector)
            labels.append(1 if is_healthy else 0)
        
        logger.info(f"Generated {n_samples} synthetic training samples")
        return np.array(features), np.array(labels)
    
    def train(self, test_size: float = 0.2) -> Dict[str, Any]:
        """
        Train the validator model.
        
        Args:
            test_size: Proportion of data for testing
            
        Returns:
            Training results
        """
        logger.info("Starting model training...")
        
        # Load data
        X, y = self.load_training_data()
        
        if len(X) == 0:
            raise ValueError("No training data available")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # Scale features
        self.validator_model.scaler.fit(X_train)
        X_train_scaled = self.validator_model.scaler.transform(X_train)
        X_test_scaled = self.validator_model.scaler.transform(X_test)
        
        # Train model
        self.validator_model.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        
        self.validator_model.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = self.validator_model.model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        report = classification_report(y_test, y_pred, output_dict=True)
        
        logger.info(f"Training complete - Accuracy: {accuracy:.4f}")
        
        # Save model
        self.validator_model.save_model()
        
        return {
            "accuracy": float(accuracy),
            "classification_report": report,
            "train_samples": len(X_train),
            "test_samples": len(X_test)
        }


if __name__ == "__main__":
    trainer = ValidatorTrainer()
    results = trainer.train()
    print(f"Training complete: {results}")

