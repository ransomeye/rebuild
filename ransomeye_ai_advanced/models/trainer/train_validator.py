# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/models/trainer/train_validator.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Script to train the hallucination checker (binary classifier)

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
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("ML libraries not available. Install: pip install scikit-learn")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidatorTrainer:
    """
    Trainer for hallucination validator model.
    Trains a binary classifier to detect hallucinations.
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
            'VALIDATOR_MODEL_PATH',
            str(Path(__file__).parent.parent.parent / 'models' / 'validator_model.pkl')
        )
        self.training_data_path = training_data_path or os.environ.get(
            'VALIDATOR_TRAINING_DATA',
            str(Path(__file__).parent.parent.parent / 'data' / 'validator_training.json')
        )
        
        self.vectorizer = None
        self.model = None
    
    def load_training_data(self) -> List[Dict]:
        """
        Load training data from JSON file.
        
        Expected format:
        [
            {
                "answer": "text of answer",
                "context": "text of context",
                "label": 1  # 1 = valid, 0 = hallucination
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
        """Generate synthetic training data for initial model."""
        logger.info("Generating synthetic training data...")
        
        # Valid examples (high similarity)
        valid_examples = [
            {
                "answer": "The system detected a suspicious login attempt from IP 192.168.1.100 at 14:30 UTC.",
                "context": "Security logs show login attempt from 192.168.1.100 at 14:30:15 UTC. Status: failed.",
                "label": 1
            },
            {
                "answer": "Multiple failed authentication attempts were observed.",
                "context": "Authentication logs indicate 5 failed login attempts in the last hour.",
                "label": 1
            },
            {
                "answer": "The threat intelligence feed reported a new malware variant.",
                "context": "Threat intel update: New malware variant detected with hash abc123.",
                "label": 1
            }
        ]
        
        # Hallucination examples (low similarity or contradictions)
        hallucination_examples = [
            {
                "answer": "The system detected a suspicious login from IP 10.0.0.1.",
                "context": "Security logs show login attempt from 192.168.1.100 at 14:30 UTC.",
                "label": 0
            },
            {
                "answer": "All systems are operating normally with no issues.",
                "context": "Multiple critical alerts triggered. System status: degraded.",
                "label": 0
            },
            {
                "answer": "The incident was resolved successfully.",
                "context": "Incident investigation ongoing. No resolution yet.",
                "label": 0
            }
        ]
        
        # Repeat to get more data
        data = (valid_examples * 10) + (hallucination_examples * 10)
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
            Tuple of (features, labels)
        """
        if not ML_AVAILABLE:
            raise ImportError("ML libraries required for training")
        
        answers = [item['answer'] for item in data]
        contexts = [item['context'] for item in data]
        labels = np.array([item['label'] for item in data])
        
        # Combine answer and context for vectorization
        combined_texts = [f"{ans} {ctx}" for ans, ctx in zip(answers, contexts)]
        
        # Initialize vectorizer
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        text_vectors = self.vectorizer.fit_transform(combined_texts).toarray()
        
        # Calculate similarity features
        similarities = []
        for ans, ctx in zip(answers, contexts):
            sim = self._calculate_similarity(ans, ctx)
            similarities.append(sim)
        
        similarities = np.array(similarities).reshape(-1, 1)
        
        # Additional features
        answer_lengths = np.array([len(ans) for ans in answers]).reshape(-1, 1)
        context_lengths = np.array([len(ctx) for ctx in contexts]).reshape(-1, 1)
        
        # Combine all features
        features = np.hstack([
            text_vectors,
            similarities,
            answer_lengths,
            context_lengths
        ])
        
        return features, labels
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words1 = words1 - stop_words
        words2 = words2 - stop_words
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def train(
        self,
        test_size: float = 0.2,
        n_estimators: int = 100
    ) -> Dict[str, Any]:
        """
        Train the validator model.
        
        Args:
            test_size: Fraction of data for testing
            n_estimators: Number of trees for RandomForest
            
        Returns:
            Training metrics
        """
        if not ML_AVAILABLE:
            raise ImportError("ML libraries required for training")
        
        # Load data
        data = self.load_training_data()
        if len(data) < 10:
            raise ValueError("Insufficient training data (need at least 10 examples)")
        
        # Prepare features
        features, labels = self.prepare_features(data)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            features, labels, test_size=test_size, random_state=42, stratify=labels
        )
        
        # Train model
        logger.info(f"Training model with {len(X_train)} examples...")
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        logger.info(f"Model accuracy: {accuracy:.2%}")
        logger.info("\nClassification Report:")
        logger.info(classification_report(y_test, y_pred))
        
        # Save model
        self.save_model()
        
        return {
            'accuracy': float(accuracy),
            'train_size': len(X_train),
            'test_size': len(X_test),
            'classification_report': classification_report(y_test, y_pred, output_dict=True)
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
        
        logger.info(f"Saved model to {self.model_output_path}")


def main():
    """Main training script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Train hallucination validator model')
    parser.add_argument('--data', type=str, help='Path to training data JSON')
    parser.add_argument('--output', type=str, help='Path to save model')
    parser.add_argument('--test-size', type=float, default=0.2, help='Test set size')
    parser.add_argument('--n-estimators', type=int, default=100, help='Number of trees')
    
    args = parser.parse_args()
    
    trainer = ValidatorTrainer(
        model_output_path=args.output,
        training_data_path=args.data
    )
    
    metrics = trainer.train(
        test_size=args.test_size,
        n_estimators=args.n_estimators
    )
    
    print(f"\nTraining complete!")
    print(f"Accuracy: {metrics['accuracy']:.2%}")
    print(f"Model saved to: {trainer.model_output_path}")


if __name__ == '__main__':
    main()

