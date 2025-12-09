# Path and File Name : /home/ransomeye/rebuild/ransomeye_hnmp_engine/ml/incremental_trainer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Autolearn loop that retrains model with analyst feedback

import os
import sys
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ransomeye_hnmp_engine.ml.risk_model import RiskModel
from ransomeye_hnmp_engine.storage.host_db import HostDB
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IncrementalTrainer:
    """
    Autolearn system that retrains risk model with analyst feedback.
    """
    
    def __init__(self, batch_size: int = 100, min_feedback: int = 10):
        """
        Initialize incremental trainer.
        
        Args:
            batch_size: Number of feedback samples to collect before retraining
            min_feedback: Minimum feedback samples required for retraining
        """
        self.batch_size = batch_size
        self.min_feedback = min_feedback
        self.model = RiskModel()
        self.host_db = HostDB()
    
    def collect_feedback_data(self):
        """
        Collect feedback data from database (scores with analyst overrides).
        
        Returns:
            Tuple of (X, y) feature and target arrays
        """
        # This would query a feedback table in production
        # For now, return empty arrays as placeholder
        # In production, would query: SELECT host_id, actual_risk_factor FROM feedback_table WHERE analyst_override = true
        
        # Placeholder: return empty arrays
        # Real implementation would query feedback records
        return np.array([]).reshape(0, 6), np.array([])
    
    def retrain_with_feedback(self, X_feedback: np.ndarray, y_feedback: np.ndarray):
        """
        Retrain model with feedback data combined with existing training data.
        
        Args:
            X_feedback: Feedback feature vectors
            y_feedback: Feedback risk factors (ground truth from analysts)
        """
        if len(X_feedback) < self.min_feedback:
            logger.info(f"Insufficient feedback data ({len(X_feedback)} < {self.min_feedback}), skipping retrain")
            return
        
        logger.info(f"Retraining model with {len(X_feedback)} feedback samples...")
        
        try:
            # Combine with synthetic baseline data
            from .train_risk import generate_synthetic_training_data
            X_synth, y_synth = generate_synthetic_training_data(n_samples=500)
            
            # Combine datasets
            X_combined = np.vstack([X_synth, X_feedback])
            y_combined = np.concatenate([y_synth, y_feedback])
            
            # Retrain
            scores = self.model.train(X_combined, y_combined, test_size=0.2)
            
            logger.info(f"Model retrained successfully:")
            logger.info(f"  Train R²: {scores['train_score']:.4f}")
            logger.info(f"  Test R²: {scores['test_score']:.4f}")
            
        except Exception as e:
            logger.error(f"Error retraining model: {e}")
    
    def run_autolearn_cycle(self):
        """
        Run one autolearn cycle (collect feedback and retrain if enough data).
        """
        logger.info("Running autolearn cycle...")
        
        X_feedback, y_feedback = self.collect_feedback_data()
        
        if len(X_feedback) >= self.min_feedback:
            self.retrain_with_feedback(X_feedback, y_feedback)
        else:
            logger.info(f"Not enough feedback data ({len(X_feedback)}/{self.min_feedback}), skipping retrain")

