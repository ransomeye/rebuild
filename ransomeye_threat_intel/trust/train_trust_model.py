# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/trust/train_trust_model.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Training script for trust scoring model

import os
import sys
import json
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

# Try to import ML libraries
try:
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("scikit-learn not available")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrustModelTrainer:
    """
    Trains trust scoring model.
    """
    
    def __init__(self, model_output_path: Optional[str] = None):
        """
        Initialize trainer.
        
        Args:
            model_output_path: Path to save model
        """
        self.model_output_path = model_output_path or os.environ.get(
            'TRUST_MODEL_PATH',
            str(Path(__file__).parent.parent / 'models' / 'trust_model.pkl')
        )
        self.model = None
    
    def load_training_data(self, data_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Load training data.
        
        Args:
            data_path: Path to training data JSON
            
        Returns:
            List of training examples
        """
        if not data_path:
            data_path = os.environ.get('TRUST_TRAINING_DATA')
        
        if data_path and os.path.exists(data_path):
            with open(data_path, 'r') as f:
                return json.load(f)
        
        # Generate synthetic data
        return self._generate_synthetic_data()
    
    def _generate_synthetic_data(self) -> List[Dict[str, Any]]:
        """Generate synthetic training data."""
        data = []
        
        # High trust examples
        for _ in range(50):
            data.append({
                'source_reputation': 0.8 + np.random.random() * 0.2,
                'age_days': np.random.random() * 365,
                'sightings_count': int(10 + np.random.random() * 90),
                'trust_label': 1  # High trust
            })
        
        # Low trust examples
        for _ in range(50):
            data.append({
                'source_reputation': np.random.random() * 0.3,
                'age_days': np.random.random() * 30,
                'sightings_count': int(np.random.random() * 5),
                'trust_label': 0  # Low trust
            })
        
        return data
    
    def train(self, test_size: float = 0.2) -> Dict[str, Any]:
        """
        Train trust model.
        
        Args:
            test_size: Test set size
            
        Returns:
            Training metrics
        """
        if not ML_AVAILABLE:
            raise ImportError("ML libraries required")
        
        # Load data
        data = self.load_training_data()
        
        # Prepare features
        features = np.array([[
            item['source_reputation'],
            item['age_days'],
            item['sightings_count']
        ] for item in data])
        
        labels = np.array([item['trust_label'] for item in data])
        
        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            features, labels, test_size=test_size, random_state=42
        )
        
        # Train
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        logger.info(f"Trust model accuracy: {accuracy:.2%}")
        
        # Save
        os.makedirs(os.path.dirname(self.model_output_path), exist_ok=True)
        with open(self.model_output_path, 'wb') as f:
            pickle.dump({'model': self.model}, f)
        
        return {
            'accuracy': float(accuracy),
            'train_size': len(X_train),
            'test_size': len(X_test)
        }


def main():
    """Main training script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Train trust scoring model')
    parser.add_argument('--data', type=str, help='Training data JSON')
    parser.add_argument('--output', type=str, help='Output model path')
    
    args = parser.parse_args()
    
    trainer = TrustModelTrainer(model_output_path=args.output)
    metrics = trainer.train()
    print(json.dumps(metrics, indent=2))


if __name__ == '__main__':
    main()

