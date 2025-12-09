# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/training/train_ranker.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Training script for re-ranker model

import os
import pickle
import json
from pathlib import Path
from typing import List, Dict, Tuple
import logging

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
    logger.error("scikit-learn not available. Install: pip install scikit-learn")


class RankerTrainer:
    """
    Trainer for re-ranker model.
    Trains on query-document pairs with relevance scores.
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
        
        self.model = None
        self.feature_names = [
            'query_length', 'doc_length', 'query_doc_overlap',
            'bm25_score', 'vector_similarity', 'doc_position'
        ]
    
    def extract_features(self, query: str, document: str, bm25_score: float, vector_score: float, position: int) -> List[float]:
        """Extract features from query-document pair."""
        return [
            len(query),
            len(document),
            len(set(query.lower().split()) & set(document.lower().split())) / max(len(set(query.lower().split())), 1),
            bm25_score,
            vector_score,
            float(position)
        ]
    
    def train(self, training_data: List[Dict], test_size: float = 0.2) -> Dict:
        """
        Train re-ranker model.
        
        Args:
            training_data: List of dicts with 'query', 'document', 'bm25_score', 'vector_score', 'position', 'relevance_score'
            test_size: Fraction for testing
            
        Returns:
            Training results
        """
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn not available")
        
        # Extract features and labels
        X = []
        y = []
        
        for item in training_data:
            features = self.extract_features(
                query=item['query'],
                document=item['document'],
                bm25_score=item.get('bm25_score', 0.0),
                vector_score=item.get('vector_score', 0.0),
                position=item.get('position', 0)
            )
            X.append(features)
            y.append(item['relevance_score'])
        
        X = np.array(X)
        y = np.array(y)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
        
        # Train model
        self.model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        self.model.fit(X_train, y_train)
        
        # Evaluate
        y_train_pred = self.model.predict(X_train)
        y_test_pred = self.model.predict(X_test)
        
        train_mse = mean_squared_error(y_train, y_train_pred)
        test_mse = mean_squared_error(y_test, y_test_pred)
        test_mae = mean_absolute_error(y_test, y_test_pred)
        
        results = {
            'train_mse': float(train_mse),
            'test_mse': float(test_mse),
            'test_mae': float(test_mae),
            'feature_importance': {
                name: float(imp) for name, imp in zip(self.feature_names, self.model.feature_importances_)
            }
        }
        
        logger.info(f"Training completed. Test MSE: {test_mse:.4f}, MAE: {test_mae:.4f}")
        return results
    
    def save_model(self, model_id: str) -> str:
        """Save trained model."""
        if self.model is None:
            raise RuntimeError("No model trained")
        
        model_data = {
            'model': self.model,
            'feature_names': self.feature_names
        }
        
        model_file = self.model_output_dir / f"ranker_{model_id}.pkl"
        with open(model_file, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Saved ranker model to {model_file}")
        return str(model_file)
    
    def load_training_data(self, data_path: str) -> List[Dict]:
        """Load training data from JSON file."""
        with open(data_path, 'r') as f:
            return json.load(f)

