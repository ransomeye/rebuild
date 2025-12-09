# Path and File Name : /home/ransomeye/rebuild/ransomeye_dpi_probe/ml/incremental_trainer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Autolearn loop for incremental model training with feedback data

import os
import json
import logging
import numpy as np
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import threading
import time

from .asset_classifier import AssetClassifier

logger = logging.getLogger(__name__)


class IncrementalTrainer:
    """Incremental trainer for autolearn functionality."""
    
    def __init__(self, classifier: AssetClassifier, feedback_dir: str):
        """
        Initialize incremental trainer.
        
        Args:
            classifier: AssetClassifier instance to retrain
            feedback_dir: Directory containing feedback JSON files
        """
        self.classifier = classifier
        self.feedback_dir = Path(feedback_dir)
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
        
        self.running = False
        self.training_thread: Optional[threading.Thread] = None
        self.min_samples_for_retrain = int(os.environ.get('PROBE_MIN_SAMPLES_RETRAIN', '100'))
        self.retrain_interval = int(os.environ.get('PROBE_RETRAIN_INTERVAL_SEC', '3600'))
        
        self.processed_files = set()
        self.lock = threading.Lock()
    
    def _load_feedback_data(self) -> List[Dict[str, Any]]:
        """Load feedback data from JSON files."""
        feedback_data = []
        
        for feedback_file in self.feedback_dir.glob('*.json'):
            if feedback_file.name in self.processed_files:
                continue
            
            try:
                with open(feedback_file, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        feedback_data.extend(data)
                    else:
                        feedback_data.append(data)
                
                self.processed_files.add(feedback_file.name)
            except Exception as e:
                logger.error(f"Error loading feedback file {feedback_file}: {e}")
        
        return feedback_data
    
    def _prepare_training_data(self, feedback_data: List[Dict[str, Any]]) -> Optional[tuple]:
        """
        Prepare training data from feedback.
        
        Args:
            feedback_data: List of feedback dictionaries
            
        Returns:
            Tuple of (X, y) or None if insufficient data
        """
        if len(feedback_data) < self.min_samples_for_retrain:
            logger.debug(f"Insufficient feedback samples: {len(feedback_data)} < {self.min_samples_for_retrain}")
            return None
        
        X = []
        y = []
        
        for item in feedback_data:
            # Extract features from flow data
            if 'flow_data' in item:
                flow_data = item['flow_data']
                features = self.classifier.extract_features(flow_data)
                X.append(features)
                
                # Get label from feedback
                label = item.get('correct_label', item.get('label'))
                if isinstance(label, str):
                    # Map to class index
                    try:
                        label_idx = self.classifier.CLASS_LABELS.index(label)
                    except ValueError:
                        label_idx = 0  # Default to normal
                else:
                    label_idx = int(label)
                
                y.append(label_idx)
        
        if len(X) < self.min_samples_for_retrain:
            return None
        
        return np.array(X), np.array(y)
    
    def _retrain_model(self, X: np.ndarray, y: np.ndarray):
        """Retrain the classifier model incrementally."""
        try:
            logger.info(f"Starting incremental retrain with {len(X)} samples")
            
            # Get existing training data if available (warm start)
            # For simplicity, we'll do a full retrain with new data
            # In production, could use partial_fit or warm_start
            
            # Retrain scaler
            self.classifier.scaler.fit(X)
            X_scaled = self.classifier.scaler.transform(X)
            
            # Retrain model
            # Use warm_start to add trees incrementally
            if hasattr(self.classifier.model, 'warm_start'):
                n_estimators_before = self.classifier.model.n_estimators
                self.classifier.model.set_params(n_estimators=n_estimators_before + 50, warm_start=True)
                self.classifier.model.fit(X_scaled, y)
            else:
                # Full retrain with more trees
                self.classifier.model = RandomForestClassifier(
                    n_estimators=self.classifier.model.n_estimators + 50,
                    max_depth=25,
                    min_samples_split=5,
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=-1,
                    class_weight='balanced'
                )
                self.classifier.model.fit(X_scaled, y)
            
            # Reinitialize SHAP explainer
            try:
                from .shap_support import SHAPExplainer
                self.classifier.shap_explainer = SHAPExplainer(
                    self.classifier.model, 
                    self.classifier.FEATURE_NAMES
                )
            except Exception as e:
                logger.warning(f"Could not reinitialize SHAP explainer: {e}")
            
            # Save model
            model_dir = Path(self.classifier.model_path)
            model_dir.mkdir(parents=True, exist_ok=True)
            self.classifier.save_model(model_dir)
            
            logger.info("Incremental retrain completed successfully")
            
        except Exception as e:
            logger.error(f"Error during incremental retrain: {e}")
    
    def _training_loop(self):
        """Background training loop."""
        logger.info("Incremental training loop started")
        
        while self.running:
            try:
                time.sleep(self.retrain_interval)
                
                if not self.running:
                    break
                
                # Load feedback data
                feedback_data = self._load_feedback_data()
                
                if not feedback_data:
                    logger.debug("No new feedback data available")
                    continue
                
                # Prepare training data
                training_data = self._prepare_training_data(feedback_data)
                
                if training_data is None:
                    logger.debug("Insufficient data for retraining")
                    continue
                
                X, y = training_data
                
                # Retrain model
                with self.lock:
                    self._retrain_model(X, y)
                
            except Exception as e:
                logger.error(f"Error in training loop: {e}")
        
        logger.info("Incremental training loop stopped")
    
    def add_feedback(self, flow_data: Dict[str, Any], predicted_label: str, 
                    correct_label: str, confidence: float = None):
        """
        Add feedback for a classification.
        
        Args:
            flow_data: Flow statistics dictionary
            predicted_label: Label predicted by classifier
            correct_label: Correct label (from human feedback or ground truth)
            confidence: Prediction confidence
        """
        if predicted_label == correct_label:
            return  # No need to record if correct
        
        feedback_entry = {
            'timestamp': datetime.now().isoformat(),
            'flow_data': flow_data,
            'predicted_label': predicted_label,
            'correct_label': correct_label,
            'confidence': confidence,
            'needs_training': True
        }
        
        # Save to feedback file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        feedback_file = self.feedback_dir / f"feedback_{timestamp}_{len(self.processed_files)}.json"
        
        try:
            # Load existing feedback if file exists
            existing_feedback = []
            if feedback_file.exists():
                with open(feedback_file, 'r') as f:
                    existing_feedback = json.load(f)
                    if not isinstance(existing_feedback, list):
                        existing_feedback = [existing_feedback]
            
            existing_feedback.append(feedback_entry)
            
            with open(feedback_file, 'w') as f:
                json.dump(existing_feedback, f, indent=2)
            
            logger.debug(f"Saved feedback to {feedback_file}")
            
        except Exception as e:
            logger.error(f"Error saving feedback: {e}")
    
    def start(self):
        """Start incremental training loop."""
        if self.running:
            logger.warning("Incremental trainer already running")
            return
        
        logger.info("Starting incremental trainer...")
        self.running = True
        
        self.training_thread = threading.Thread(target=self._training_loop, daemon=True)
        self.training_thread.start()
    
    def stop(self):
        """Stop incremental training loop."""
        if not self.running:
            return
        
        logger.info("Stopping incremental trainer...")
        self.running = False
        
        if self.training_thread:
            self.training_thread.join(timeout=5)
    
    def trigger_retrain(self):
        """Manually trigger retraining."""
        feedback_data = self._load_feedback_data()
        if not feedback_data:
            logger.warning("No feedback data available for retraining")
            return
        
        training_data = self._prepare_training_data(feedback_data)
        if training_data is None:
            logger.warning("Insufficient data for retraining")
            return
        
        X, y = training_data
        with self.lock:
            self._retrain_model(X, y)

