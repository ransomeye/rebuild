# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/models/trainer/train_reranker.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Script to train context reranking model

import os
import sys
import pickle
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging

# Try to import ML libraries
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import ndcg_score
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("ML libraries not available. Install: pip install scikit-learn")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RerankerTrainer:
    """
    Trainer for context reranking model.
    Trains a model to score and rerank retrieved context chunks.
    """
    
    def __init__(
        self,
        model_output_path: Optional[str] = None,
        training_data_path: Optional[str] = None
    ):
        """
        Initialize trainer.
        
        Args:
            model_output_path: Path to save trained model
            training_data_path: Path to training data JSON
        """
        self.model_output_path = model_output_path or os.environ.get(
            'RERANKER_MODEL_PATH',
            str(Path(__file__).parent.parent.parent / 'models' / 'reranker_model.pkl')
        )
        self.training_data_path = training_data_path or os.environ.get(
            'RERANKER_TRAINING_DATA',
            str(Path(__file__).parent.parent.parent / 'data' / 'reranker_training.json')
        )
        
        self.vectorizer = None
        self.model = None
    
    def load_training_data(self) -> List[Dict]:
        """
        Load training data from JSON file.
        
        Expected format:
        [
            {
                "query": "user query",
                "chunks": [
                    {"text": "chunk text", "relevance_score": 0.9},
                    {"text": "chunk text", "relevance_score": 0.3},
                    ...
                ]
            },
            ...
        ]
        
        Returns:
            List of training examples
        """
        if not os.path.exists(self.training_data_path):
            logger.warning(f"Training data not found at {self.training_data_path}")
            logger.info("Generating synthetic training data...")
            return self._generate_synthetic_data()
        
        try:
            with open(self.training_data_path, 'r') as f:
                data = json.load(f)
            logger.info(f"Loaded {len(data)} training examples")
            return data
        except Exception as e:
            logger.error(f"Error loading training data: {e}")
            return self._generate_synthetic_data()
    
    def _generate_synthetic_data(self) -> List[Dict]:
        """Generate synthetic training data."""
        logger.info("Generating synthetic training data...")
        
        examples = [
            {
                "query": "suspicious login attempt",
                "chunks": [
                    {
                        "text": "Security logs show failed login attempt from IP 192.168.1.100 at 14:30 UTC.",
                        "relevance_score": 0.95
                    },
                    {
                        "text": "System uptime: 30 days. All services operational.",
                        "relevance_score": 0.1
                    },
                    {
                        "text": "Multiple authentication failures detected in the last hour.",
                        "relevance_score": 0.85
                    }
                ]
            },
            {
                "query": "malware detection",
                "chunks": [
                    {
                        "text": "Threat intel: New malware variant detected with hash abc123.",
                        "relevance_score": 0.9
                    },
                    {
                        "text": "Network traffic analysis shows normal patterns.",
                        "relevance_score": 0.2
                    },
                    {
                        "text": "Antivirus scan completed. No threats found.",
                        "relevance_score": 0.3
                    }
                ]
            }
        ]
        
        # Repeat to get more data
        data = examples * 20
        logger.info(f"Generated {len(data)} synthetic training examples")
        return data
    
    def prepare_features(
        self,
        data: List[Dict]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare features from training data.
        
        Args:
            data: Training data
            
        Returns:
            Tuple of (features, scores)
        """
        if not ML_AVAILABLE:
            raise ImportError("ML libraries required for training")
        
        features_list = []
        scores_list = []
        
        for example in data:
            query = example['query']
            chunks = example['chunks']
            
            for chunk in chunks:
                chunk_text = chunk['text']
                relevance_score = chunk['relevance_score']
                
                # Combine query and chunk
                combined_text = f"{query} {chunk_text}"
                features_list.append(combined_text)
                scores_list.append(relevance_score)
        
        # Vectorize
        self.vectorizer = TfidfVectorizer(max_features=500, stop_words='english')
        features = self.vectorizer.fit_transform(features_list).toarray()
        
        # Additional features
        query_lengths = np.array([len(f.split()[0]) for f in features_list]).reshape(-1, 1)
        chunk_lengths = np.array([len(f.split()[1:]) for f in features_list]).reshape(-1, 1)
        
        # Combine features
        combined_features = np.hstack([
            features,
            query_lengths,
            chunk_lengths
        ])
        
        scores = np.array(scores_list)
        
        return combined_features, scores
    
    def train(
        self,
        test_size: float = 0.2
    ) -> Dict[str, Any]:
        """
        Train the reranker model.
        
        Args:
            test_size: Fraction of data for testing
            
        Returns:
            Training metrics
        """
        if not ML_AVAILABLE:
            raise ImportError("ML libraries required for training")
        
        # Load data
        data = self.load_training_data()
        if len(data) < 5:
            raise ValueError("Insufficient training data")
        
        # Prepare features
        features, scores = self.prepare_features(data)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            features, scores, test_size=test_size, random_state=42
        )
        
        # Train model (regression for scoring)
        logger.info(f"Training reranker with {len(X_train)} examples...")
        self.model = LogisticRegression(random_state=42, max_iter=1000)
        
        # Convert scores to binary for classification (relevance >= 0.5)
        y_train_binary = (y_train >= 0.5).astype(int)
        y_test_binary = (y_test >= 0.5).astype(int)
        
        self.model.fit(X_train, y_train_binary)
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        accuracy = np.mean(y_pred == y_test_binary)
        
        logger.info(f"Model accuracy: {accuracy:.2%}")
        
        # Save model
        self.save_model()
        
        return {
            'accuracy': float(accuracy),
            'train_size': len(X_train),
            'test_size': len(X_test)
        }
    
    def save_model(self):
        """Save trained model and vectorizer."""
        if not self.model or not self.vectorizer:
            raise ValueError("Model not trained yet")
        
        os.makedirs(os.path.dirname(self.model_output_path), exist_ok=True)
        
        model_data = {
            'model': self.model,
            'vectorizer': self.vectorizer
        }
        
        with open(self.model_output_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Saved reranker model to {self.model_output_path}")


def main():
    """Main training script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Train context reranker model')
    parser.add_argument('--data', type=str, help='Path to training data JSON')
    parser.add_argument('--output', type=str, help='Path to save model')
    parser.add_argument('--test-size', type=float, default=0.2, help='Test set size')
    
    args = parser.parse_args()
    
    trainer = RerankerTrainer(
        model_output_path=args.output,
        training_data_path=args.data
    )
    
    metrics = trainer.train(test_size=args.test_size)
    
    print(f"\nTraining complete!")
    print(f"Accuracy: {metrics['accuracy']:.2%}")
    print(f"Model saved to: {trainer.model_output_path}")


if __name__ == '__main__':
    main()

