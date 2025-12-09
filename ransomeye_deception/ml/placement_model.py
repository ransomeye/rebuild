# Path and File Name : /home/ransomeye/rebuild/ransomeye_deception/ml/placement_model.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Wrapper for scikit-learn model that predicts utility_score for decoy placement

import os
import sys
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import scikit-learn
try:
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.linear_model import LogisticRegression
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available, using simple heuristic model")


class PlacementModel:
    """
    ML model for predicting attractiveness score of decoy placement locations.
    Inputs: host_criticality, segment, existing_density, decoy_type
    Output: utility_score (0.0 to 1.0)
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize placement model.
        
        Args:
            model_path: Path to saved model file
        """
        self.model = None
        self.model_path = model_path or os.environ.get(
            'DECEPTION_MODEL_PATH',
            str(Path(__file__).parent / 'placement_model.pkl')
        )
        
        self.feature_names = [
            'host_criticality',
            'segment_hash',
            'existing_density',
            'decoy_type_hash',
            'type_specific_feature'
        ]
        
        self._load_or_create_model()
    
    def _load_or_create_model(self):
        """Load existing model or create new one."""
        model_file = Path(self.model_path)
        
        if model_file.exists():
            try:
                with open(model_file, 'rb') as f:
                    self.model = pickle.load(f)
                logger.info(f"Loaded placement model from {self.model_path}")
                return
            except Exception as e:
                logger.warning(f"Failed to load model: {e}, creating new one")
        
        # Create new model
        self._create_default_model()
        
        # Save it
        try:
            model_file.parent.mkdir(parents=True, exist_ok=True)
            with open(model_file, 'wb') as f:
                pickle.dump(self.model, f)
            logger.info(f"Created and saved new placement model to {self.model_path}")
        except Exception as e:
            logger.warning(f"Failed to save model: {e}")
    
    def _create_default_model(self):
        """Create a default trained model."""
        if not SKLEARN_AVAILABLE:
            # Fallback to simple heuristic
            self.model = None
            logger.info("Using heuristic placement model (scikit-learn not available)")
            return
        
        # Create model with default training data
        # In production, this would be trained on historical hit rates
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        
        # Generate synthetic training data based on heuristics
        X_train, y_train = self._generate_training_data()
        
        # Train model
        self.model.fit(X_train, y_train)
        logger.info("Created and trained default placement model")
    
    def _generate_training_data(self, n_samples: int = 1000) -> tuple:
        """
        Generate synthetic training data.
        
        Args:
            n_samples: Number of training samples
            
        Returns:
            Tuple of (X, y) arrays
        """
        np.random.seed(42)
        
        # Generate features
        X = np.random.rand(n_samples, 5)
        
        # Feature 0: host_criticality (0-1)
        X[:, 0] = np.random.beta(2, 5, n_samples)
        
        # Feature 1: segment_hash (0-1)
        X[:, 1] = np.random.rand(n_samples)
        
        # Feature 2: existing_density (0-1)
        X[:, 2] = np.random.beta(1, 3, n_samples)
        
        # Feature 3: decoy_type_hash (0-1)
        X[:, 3] = np.random.rand(n_samples)
        
        # Feature 4: type_specific_feature (0-1)
        X[:, 4] = np.random.rand(n_samples)
        
        # Generate targets based on heuristics:
        # Higher host_criticality -> higher utility
        # Lower existing_density -> higher utility (less crowded)
        # Some interaction effects
        y = (
            0.3 * X[:, 0] +  # host_criticality
            0.2 * X[:, 1] +  # segment_hash
            -0.3 * X[:, 2] +  # existing_density (negative)
            0.1 * X[:, 3] +  # decoy_type_hash
            0.1 * X[:, 4] +  # type_specific_feature
            0.2 * X[:, 0] * X[:, 1] +  # interaction
            np.random.normal(0, 0.05, n_samples)  # noise
        )
        
        # Clip to [0, 1]
        y = np.clip(y, 0.0, 1.0)
        
        return X, y
    
    def predict_attractiveness(self, features: np.ndarray) -> float:
        """
        Predict attractiveness score for given features.
        
        Args:
            features: Feature vector (1D or 2D array)
            
        Returns:
            Attractiveness score (0.0 to 1.0)
        """
        # Ensure 2D array
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        if self.model is None:
            # Heuristic fallback
            return self._heuristic_score(features[0])
        
        try:
            score = self.model.predict(features)[0]
            return float(np.clip(score, 0.0, 1.0))
        except Exception as e:
            logger.error(f"Error predicting attractiveness: {e}")
            return self._heuristic_score(features[0])
    
    def _heuristic_score(self, features: np.ndarray) -> float:
        """
        Heuristic fallback scoring.
        
        Args:
            features: Feature vector
            
        Returns:
            Score
        """
        host_criticality = features[0] if len(features) > 0 else 0.5
        existing_density = features[2] if len(features) > 2 else 0.0
        
        # Simple heuristic: high criticality, low density = high score
        score = 0.6 * host_criticality + 0.4 * (1.0 - existing_density)
        return float(np.clip(score, 0.0, 1.0))
    
    def update_model(self, X_new: np.ndarray, y_new: np.ndarray):
        """
        Update model with new data (incremental learning).
        
        Args:
            X_new: New feature vectors
            y_new: New target values
        """
        if self.model is None or not SKLEARN_AVAILABLE:
            logger.warning("Cannot update heuristic model")
            return
        
        try:
            # For GradientBoostingRegressor, we'd need to retrain
            # In production, use partial_fit models or retrain periodically
            logger.info("Model update requires retraining (not implemented in this version)")
        except Exception as e:
            logger.error(f"Error updating model: {e}")

