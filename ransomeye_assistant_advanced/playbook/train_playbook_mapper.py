# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant_advanced/playbook/train_playbook_mapper.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Training script for playbook mapper model using feedback data

import os
import pickle
import json
from pathlib import Path
from typing import List, Dict, Any
import logging

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.error("scikit-learn not available - cannot train model")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlaybookMapperTrainer:
    """Trainer for playbook mapper model."""
    
    def __init__(self, model_path: str, feedback_dir: str = None):
        """
        Initialize trainer.
        
        Args:
            model_path: Path to save trained model
            feedback_dir: Directory containing feedback data
        """
        self.model_path = model_path
        self.feedback_dir = feedback_dir or os.environ.get('FEEDBACK_DIR', '/var/lib/ransomeye/feedback')
        self.vectorizer = None
        self.model = None
    
    def load_training_data(self) -> tuple:
        """
        Load training data from feedback files.
        
        Returns:
            Tuple of (texts, labels)
        """
        texts = []
        labels = []
        
        feedback_path = Path(self.feedback_dir)
        if not feedback_path.exists():
            logger.warning(f"Feedback directory not found: {feedback_path}")
            return texts, labels
        
        # Load feedback JSON files
        for feedback_file in feedback_path.glob("*.json"):
            try:
                with open(feedback_file, 'r') as f:
                    data = json.load(f)
                    
                    # Extract training examples from accepted feedback
                    if data.get('accepted', False):
                        summary = data.get('incident_summary', '')
                        playbook_id = data.get('playbook_id')
                        
                        if summary and playbook_id:
                            texts.append(summary)
                            labels.append(playbook_id)
                            
            except Exception as e:
                logger.warning(f"Error loading feedback file {feedback_file}: {e}")
        
        logger.info(f"Loaded {len(texts)} training examples")
        return texts, labels
    
    def train(self, texts: List[str], labels: List[int], test_size: float = 0.2):
        """
        Train playbook mapper model.
        
        Args:
            texts: Training text examples
            labels: Playbook ID labels
            test_size: Fraction of data for testing
            
        Returns:
            Training metrics
        """
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn not available - cannot train model")
        
        if len(texts) < 10:
            logger.warning("Insufficient training data - need at least 10 examples")
            return None
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=test_size, random_state=42
        )
        
        # Create vectorizer
        self.vectorizer = TfidfVectorizer(max_features=200, stop_words='english', ngram_range=(1, 2))
        X_train_vec = self.vectorizer.fit_transform(X_train)
        X_test_vec = self.vectorizer.transform(X_test)
        
        # Train model
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X_train_vec, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test_vec)
        accuracy = accuracy_score(y_test, y_pred)
        
        logger.info(f"Model accuracy: {accuracy:.3f}")
        logger.info(f"\n{classification_report(y_test, y_pred)}")
        
        # Save model
        self.save_model()
        
        return {
            'accuracy': accuracy,
            'train_size': len(X_train),
            'test_size': len(X_test)
        }
    
    def save_model(self):
        """Save trained model to disk."""
        if not self.model or not self.vectorizer:
            raise RuntimeError("Model not trained yet")
        
        Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.model_path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'vectorizer': self.vectorizer
            }, f)
        
        logger.info(f"Saved trained model to {self.model_path}")

def main():
    """Main training function."""
    model_path = os.environ.get('PLAYBOOK_MODEL_PATH', '/var/lib/ransomeye/models/playbook_matcher.pkl')
    feedback_dir = os.environ.get('FEEDBACK_DIR', '/var/lib/ransomeye/feedback')
    
    trainer = PlaybookMapperTrainer(model_path, feedback_dir)
    texts, labels = trainer.load_training_data()
    
    if texts:
        metrics = trainer.train(texts, labels)
        if metrics:
            logger.info(f"Training complete: {metrics}")
    else:
        logger.warning("No training data available")

if __name__ == "__main__":
    main()

