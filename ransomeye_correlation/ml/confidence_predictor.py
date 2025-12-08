# Path and File Name : /home/ransomeye/rebuild/ransomeye_correlation/ml/confidence_predictor.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Loads model from CONFIDENCE_MODEL_PATH and predicts confidence score (0-1) using features: num_hosts, alert_severity_sum, distinct_users, time_span

import os
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import scikit-learn
try:
    from sklearn.ensemble import RandomForestRegressor
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available, using simple scoring")

class ConfidencePredictor:
    """
    ML model for predicting correlation confidence score.
    """
    
    def __init__(self, model_path: str = None):
        """
        Initialize confidence predictor.
        
        Args:
            model_path: Path to saved model file
        """
        self.model_path = Path(model_path or os.environ.get(
            'CONFIDENCE_MODEL_PATH',
            os.path.join(os.environ.get('CORRELATION_DATA_DIR', '/home/ransomeye/rebuild/ransomeye_correlation/data'), 'confidence_model.pkl')
        ))
        self.model = None
        self.model_loaded = False
        
        if self.model_path and self.model_path.exists():
            self._load_model()
        else:
            self._create_default_model()
    
    def _create_default_model(self):
        """Create default model."""
        if SKLEARN_AVAILABLE:
            # Use RandomForest for better feature importance
            self.model = RandomForestRegressor(n_estimators=10, random_state=42)
            # Initialize with dummy data
            X_dummy = np.random.rand(10, 4)
            y_dummy = np.random.rand(10)
            self.model.fit(X_dummy, y_dummy)
            logger.info("Created default confidence predictor model (RandomForest)")
        else:
            self.model = None
            logger.warning("Using simple scoring (no ML model)")
    
    def _load_model(self):
        """Load saved model."""
        try:
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
            self.model_loaded = True
            logger.info(f"Loaded confidence model from: {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}, using default")
            self._create_default_model()
    
    def is_model_loaded(self) -> bool:
        """
        Check if model is loaded.
        
        Returns:
            True if model is loaded, False otherwise
        """
        return self.model_loaded and self.model is not None
    
    def _extract_features(self, graph_data: Dict[str, Any]) -> np.ndarray:
        """
        Extract features from graph data.
        
        Features:
        - num_hosts: Number of Host entities
        - alert_severity_sum: Sum of alert severities
        - distinct_users: Number of distinct User entities
        - time_span: Time span in hours
        
        Args:
            graph_data: Graph data dictionary
            
        Returns:
            Feature vector
        """
        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])
        
        # Count entity types
        num_hosts = sum(1 for node in nodes if node.get('type') == 'Host')
        distinct_users = len(set(node.get('value') for node in nodes if node.get('type') == 'User'))
        
        # Calculate alert severity sum (if available)
        alert_severity_sum = sum(node.get('alert_count', 0) for node in nodes)
        
        # Calculate time span (if timestamps available)
        # For now, use edge count as proxy
        time_span = len(edges) * 0.5  # Approximate hours
        
        features = np.array([
            num_hosts,
            alert_severity_sum,
            distinct_users,
            time_span
        ]).reshape(1, -1)
        
        return features
    
    def predict(self, graph_data: Dict[str, Any]) -> float:
        """
        Predict confidence score (0-1).
        
        Args:
            graph_data: Graph data dictionary
            
        Returns:
            Confidence score between 0 and 1
        """
        # Extract features
        features = self._extract_features(graph_data)
        
        # Predict using model
        if self.model and SKLEARN_AVAILABLE:
            score = self.model.predict(features)[0]
            # Clamp to [0, 1]
            score = max(0.0, min(1.0, float(score)))
        else:
            # Simple scoring based on features
            num_hosts = features[0][0]
            alert_count = features[0][1]
            score = min(1.0, (num_hosts * 0.1 + alert_count * 0.01))
        
        return score

