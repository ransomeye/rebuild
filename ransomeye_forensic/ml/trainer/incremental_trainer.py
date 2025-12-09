# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/ml/trainer/incremental_trainer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Autolearn loop that updates model based on operator feedback

import os
import pickle
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import ML libraries
try:
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.error("scikit-learn not available. Install: pip install scikit-learn")


class IncrementalTrainer:
    """
    Incremental trainer for autolearn functionality.
    Updates model based on operator feedback without full retraining.
    """
    
    def __init__(self, model_path: Optional[str] = None, feedback_dir: Optional[str] = None):
        """
        Initialize incremental trainer.
        
        Args:
            model_path: Path to existing model file
            feedback_dir: Directory to store feedback data
        """
        if feedback_dir is None:
            feedback_dir = os.environ.get(
                'FEEDBACK_DIR',
                '/home/ransomeye/rebuild/ransomeye_forensic/ml/feedback'
            )
        
        self.feedback_dir = Path(feedback_dir)
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
        
        self.model_path = model_path
        self.model = None
        self.scaler = None
        self.feature_names = None
        
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path: str):
        """Load existing model."""
        model_file = Path(model_path)
        if not model_file.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        with open(model_file, 'rb') as f:
            model_data = pickle.load(f)
        
        if isinstance(model_data, dict):
            self.model = model_data.get('model')
            self.scaler = model_data.get('scaler')
            self.feature_names = model_data.get('feature_names')
        else:
            self.model = model_data
        
        self.model_path = model_path
        logger.info(f"Loaded model from {model_path}")
    
    def record_feedback(
        self,
        dna_id: str,
        dna_data: Dict,
        predicted_label: bool,
        operator_label: bool,
        operator_notes: Optional[str] = None
    ) -> str:
        """
        Record operator feedback for a DNA sample.
        
        Args:
            dna_id: DNA sample identifier
            dna_data: DNA feature dictionary
            predicted_label: Label predicted by model
            operator_label: Correct label from operator
            operator_notes: Optional notes from operator
            
        Returns:
            Feedback entry ID
        """
        feedback_entry = {
            'feedback_id': f"{dna_id}_{datetime.utcnow().timestamp()}",
            'dna_id': dna_id,
            'dna_data': dna_data,
            'predicted_label': predicted_label,
            'operator_label': operator_label,
            'operator_notes': operator_notes,
            'timestamp': datetime.utcnow().isoformat(),
            'needs_retraining': predicted_label != operator_label
        }
        
        # Save feedback
        feedback_file = self.feedback_dir / f"{feedback_entry['feedback_id']}.json"
        with open(feedback_file, 'w') as f:
            json.dump(feedback_entry, f, indent=2)
        
        logger.info(f"Recorded feedback: {feedback_entry['feedback_id']}")
        
        return feedback_entry['feedback_id']
    
    def load_feedback(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Load feedback entries.
        
        Args:
            limit: Maximum number of entries to load
            
        Returns:
            List of feedback entries
        """
        feedback_files = sorted(self.feedback_dir.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
        
        if limit:
            feedback_files = feedback_files[:limit]
        
        feedback_entries = []
        for feedback_file in feedback_files:
            try:
                with open(feedback_file, 'r') as f:
                    feedback_entries.append(json.load(f))
            except Exception as e:
                logger.error(f"Error loading feedback file {feedback_file}: {e}")
        
        return feedback_entries
    
    def incremental_update(
        self,
        min_feedback_count: int = 10,
        retrain_threshold: float = 0.1
    ) -> Optional[Dict]:
        """
        Perform incremental model update based on feedback.
        
        Args:
            min_feedback_count: Minimum feedback entries needed for update
            retrain_threshold: Error rate threshold to trigger full retrain
            
        Returns:
            Update results or None if no update performed
        """
        if not SKLEARN_AVAILABLE or self.model is None:
            logger.error("Model not loaded or scikit-learn unavailable")
            return None
        
        # Load feedback
        feedback_entries = self.load_feedback()
        
        if len(feedback_entries) < min_feedback_count:
            logger.info(f"Not enough feedback ({len(feedback_entries)} < {min_feedback_count})")
            return None
        
        # Filter feedback that needs correction
        correction_feedback = [f for f in feedback_entries if f.get('needs_retraining', False)]
        
        if len(correction_feedback) == 0:
            logger.info("No corrections needed")
            return None
        
        # Calculate error rate
        error_rate = len(correction_feedback) / len(feedback_entries)
        
        if error_rate < retrain_threshold:
            logger.info(f"Error rate ({error_rate:.2%}) below threshold ({retrain_threshold:.2%})")
            return None
        
        logger.info(f"Performing incremental update with {len(correction_feedback)} corrections")
        
        # Extract features and labels from feedback
        from ..inference.classifier import ForensicClassifier
        classifier = ForensicClassifier()
        
        X_new = []
        y_new = []
        
        for feedback in correction_feedback:
            dna_data = feedback['dna_data']
            features = classifier.extract_features(dna_data)
            X_new.append(features)
            y_new.append(1 if feedback['operator_label'] else 0)
        
        X_new = np.array(X_new)
        y_new = np.array(y_new)
        
        # Scale features
        if self.scaler is not None:
            X_new_scaled = self.scaler.transform(X_new)
        else:
            X_new_scaled = X_new
        
        # Update model using partial_fit if available (for online learning)
        # Otherwise, retrain with combined dataset
        if hasattr(self.model, 'partial_fit'):
            # Online learning
            self.model.partial_fit(X_new_scaled, y_new, classes=[0, 1])
            update_method = 'partial_fit'
        else:
            # For RandomForest, we need to retrain with combined data
            # In production, would load original training data and combine
            logger.warning("Model does not support partial_fit. Full retraining required.")
            update_method = 'retrain_required'
        
        # Save updated model
        if update_method == 'partial_fit':
            model_id = f"incremental_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            updated_model_path = self._save_updated_model(model_id)
            
            return {
                'update_method': update_method,
                'updated_model_path': updated_model_path,
                'feedback_used': len(correction_feedback),
                'error_rate': error_rate
            }
        else:
            return {
                'update_method': update_method,
                'message': 'Full retraining required. Use train_classifier.py',
                'feedback_used': len(correction_feedback),
                'error_rate': error_rate
            }
    
    def _save_updated_model(self, model_id: str) -> str:
        """Save updated model."""
        model_output_dir = Path(self.model_path).parent
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'model_id': model_id,
            'updated_at': datetime.utcnow().isoformat(),
            'base_model': str(self.model_path)
        }
        
        model_filename = f"{model_id}.pkl"
        model_path = model_output_dir / model_filename
        
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Saved updated model to {model_path}")
        
        return str(model_path)

