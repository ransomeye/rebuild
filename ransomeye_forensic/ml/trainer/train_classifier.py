# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/ml/trainer/train_classifier.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Script to train the forensic classifier on operator-provided labeled data

import os
import pickle
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import ML libraries
try:
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.error("scikit-learn not available. Install: pip install scikit-learn")


class ClassifierTrainer:
    """
    Trainer for forensic classifier.
    Trains on labeled DNA data and produces model with SHAP support.
    """
    
    def __init__(self, model_output_dir: Optional[str] = None):
        """
        Initialize trainer.
        
        Args:
            model_output_dir: Directory to save trained models
        """
        if model_output_dir is None:
            model_output_dir = os.environ.get(
                'MODEL_DIR',
                '/home/ransomeye/rebuild/ransomeye_forensic/ml/models'
            )
        
        self.model_output_dir = Path(model_output_dir)
        self.model_output_dir.mkdir(parents=True, exist_ok=True)
        
        self.model = None
        self.scaler = None
        self.feature_names = None
    
    def load_training_data(self, data_path: str) -> Tuple[List[Dict], List[int]]:
        """
        Load training data from file.
        
        Args:
            data_path: Path to JSON file with labeled DNA data
            
        Returns:
            Tuple of (dna_data_list, labels_list)
        """
        data_file = Path(data_path)
        if not data_file.exists():
            raise FileNotFoundError(f"Training data not found: {data_path}")
        
        with open(data_file, 'r') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            raise ValueError("Training data must be a list of labeled examples")
        
        dna_data_list = []
        labels_list = []
        
        for example in data:
            if 'dna' not in example or 'label' not in example:
                logger.warning("Skipping example without 'dna' or 'label' field")
                continue
            
            dna_data_list.append(example['dna'])
            # Convert label to binary: 1 for malicious, 0 for benign
            label = 1 if example['label'] in ['malicious', 1, True, '1'] else 0
            labels_list.append(label)
        
        logger.info(f"Loaded {len(dna_data_list)} training examples")
        return dna_data_list, labels_list
    
    def extract_features_batch(self, dna_data_list: List[Dict]) -> np.ndarray:
        """
        Extract features from multiple DNA samples.
        
        Args:
            dna_data_list: List of DNA dictionaries
            
        Returns:
            Feature matrix (n_samples, n_features)
        """
        from ..inference.classifier import ForensicClassifier
        
        classifier = ForensicClassifier()
        features_list = []
        
        for dna_data in dna_data_list:
            features = classifier.extract_features(dna_data)
            features_list.append(features)
        
        return np.array(features_list)
    
    def train(
        self,
        dna_data_list: List[Dict],
        labels: List[int],
        test_size: float = 0.2,
        n_estimators: int = 100,
        max_depth: Optional[int] = None,
        random_state: int = 42
    ) -> Dict:
        """
        Train classifier model.
        
        Args:
            dna_data_list: List of DNA feature dictionaries
            labels: List of binary labels (0=benign, 1=malicious)
            test_size: Fraction of data for testing
            n_estimators: Number of trees in RandomForest
            max_depth: Maximum tree depth
            random_state: Random seed
            
        Returns:
            Training results dictionary
        """
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn not available. Cannot train model.")
        
        logger.info(f"Training classifier on {len(dna_data_list)} examples")
        
        # Extract features
        X = self.extract_features_batch(dna_data_list)
        y = np.array(labels)
        
        # Store feature names
        from ..inference.classifier import ForensicClassifier
        temp_classifier = ForensicClassifier()
        self.feature_names = temp_classifier.feature_names
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        logger.info("Training RandomForest classifier...")
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            n_jobs=-1,
            class_weight='balanced'
        )
        
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_train_pred = self.model.predict(X_train_scaled)
        y_test_pred = self.model.predict(X_test_scaled)
        
        train_accuracy = accuracy_score(y_train, y_train_pred)
        test_accuracy = accuracy_score(y_test, y_test_pred)
        test_precision = precision_score(y_test, y_test_pred, zero_division=0)
        test_recall = recall_score(y_test, y_test_pred, zero_division=0)
        test_f1 = f1_score(y_test, y_test_pred, zero_division=0)
        
        # Classification report
        report = classification_report(y_test, y_test_pred, output_dict=True)
        
        results = {
            'train_accuracy': float(train_accuracy),
            'test_accuracy': float(test_accuracy),
            'test_precision': float(test_precision),
            'test_recall': float(test_recall),
            'test_f1': float(test_f1),
            'classification_report': report,
            'n_train': len(X_train),
            'n_test': len(X_test),
            'feature_importance': {
                name: float(imp) for name, imp in zip(self.feature_names, self.model.feature_importances_)
            }
        }
        
        logger.info(f"Training completed. Test accuracy: {test_accuracy:.4f}, F1: {test_f1:.4f}")
        
        return results
    
    def save_model(self, model_id: str, version: str = '1.0', metadata: Optional[Dict] = None) -> str:
        """
        Save trained model to file.
        
        Args:
            model_id: Unique model identifier
            version: Model version
            metadata: Additional metadata
            
        Returns:
            Path to saved model file
        """
        if self.model is None:
            raise RuntimeError("No model trained. Call train() first.")
        
        # Create model data
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'model_id': model_id,
            'version': version,
            'trained_at': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        
        # Save model
        model_filename = f"{model_id}_v{version}.pkl"
        model_path = self.model_output_dir / model_filename
        
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Saved model to {model_path}")
        
        return str(model_path)
    
    def train_from_file(
        self,
        data_path: str,
        model_id: str,
        version: str = '1.0',
        **train_kwargs
    ) -> Dict:
        """
        Complete training pipeline from data file.
        
        Args:
            data_path: Path to training data JSON
            model_id: Model identifier
            version: Model version
            **train_kwargs: Additional training parameters
            
        Returns:
            Training results and model path
        """
        # Load data
        dna_data_list, labels = self.load_training_data(data_path)
        
        # Train
        results = self.train(dna_data_list, labels, **train_kwargs)
        
        # Save model
        model_path = self.save_model(model_id, version, metadata={'training_results': results})
        
        results['model_path'] = model_path
        results['model_id'] = model_id
        results['version'] = version
        
        return results

