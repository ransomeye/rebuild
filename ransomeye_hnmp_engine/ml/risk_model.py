# Path and File Name : /home/ransomeye/rebuild/ransomeye_hnmp_engine/ml/risk_model.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Trainable ML regressor model that predicts risk factor (0.0-1.0) from host features

import os
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RiskModel:
    """
    Trainable ML model for predicting host compromise risk factor (0.0 - 1.0).
    
    Features:
    - num_failed_high: Number of high-severity failed compliance checks
    - num_open_ports: Number of open ports
    - kernel_age_days: Age of kernel version in days
    - num_failed_critical: Number of critical failed checks
    - num_packages: Total number of installed packages
    - num_services: Number of running services
    """
    
    def __init__(self, model_dir: str = None):
        """
        Initialize risk model.
        
        Args:
            model_dir: Directory to store model files
        """
        self.model_dir = model_dir or os.environ.get('MODEL_DIR', '/home/ransomeye/rebuild/ransomeye_hnmp_engine/models')
        Path(self.model_dir).mkdir(parents=True, exist_ok=True)
        
        self.model_path = os.path.join(self.model_dir, 'risk_model.pkl')
        self.scaler_path = os.path.join(self.model_dir, 'risk_scaler.pkl')
        
        self.model: Optional[RandomForestRegressor] = None
        self.scaler: Optional[StandardScaler] = None
        self.feature_names = [
            'num_failed_high',
            'num_open_ports',
            'kernel_age_days',
            'num_failed_critical',
            'num_packages',
            'num_services'
        ]
        
        self._load_model()
    
    def _load_model(self):
        """Load trained model from disk or create default."""
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                with open(self.scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                logger.info("Loaded existing risk model")
            else:
                # Create default untrained model
                self.model = RandomForestRegressor(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    n_jobs=-1
                )
                self.scaler = StandardScaler()
                logger.info("Created default risk model (untrained)")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
            self.scaler = StandardScaler()
    
    def _extract_features(self, host_data: Dict[str, Any]) -> np.ndarray:
        """
        Extract feature vector from host data.
        
        Args:
            host_data: Host profile dictionary
            
        Returns:
            Feature vector as numpy array
        """
        profile = host_data.get('profile', host_data)
        
        # Extract features
        num_failed_high = host_data.get('num_failed_high', 0)
        num_failed_critical = host_data.get('num_failed_critical', 0)
        num_open_ports = len(profile.get('open_ports', []))
        num_packages = len(profile.get('packages', []))
        num_services = len(profile.get('services', []))
        
        # Calculate kernel age
        kernel_version = profile.get('kernel_version', '')
        kernel_age_days = host_data.get('kernel_age_days', 0)
        if kernel_age_days == 0 and kernel_version:
            # Estimate kernel age (simplified - in production, would parse version and check release dates)
            kernel_age_days = 365  # Default to 1 year
        
        features = np.array([[
            num_failed_high,
            num_open_ports,
            kernel_age_days,
            num_failed_critical,
            num_packages,
            num_services
        ]])
        
        return features
    
    def predict(self, host_data: Dict[str, Any]) -> float:
        """
        Predict risk factor for a host.
        
        Args:
            host_data: Host profile dictionary
            
        Returns:
            Risk factor (0.0 - 1.0), where 1.0 is highest risk
        """
        if self.model is None:
            logger.warning("Model not loaded, returning default risk factor")
            return 0.5
        
        try:
            features = self._extract_features(host_data)
            
            # Scale features if scaler is fitted
            if self.scaler and hasattr(self.scaler, 'mean_'):
                features_scaled = self.scaler.transform(features)
            else:
                features_scaled = features
            
            # Predict risk factor
            risk_factor = self.model.predict(features_scaled)[0]
            
            # Clamp to [0.0, 1.0]
            risk_factor = max(0.0, min(1.0, risk_factor))
            
            return float(risk_factor)
        except Exception as e:
            logger.error(f"Error predicting risk: {e}")
            return 0.5  # Default moderate risk
    
    def train(self, X: np.ndarray, y: np.ndarray, test_size: float = 0.2):
        """
        Train the risk model.
        
        Args:
            X: Feature matrix (n_samples, n_features)
            y: Target risk factors (n_samples,)
            test_size: Fraction of data to use for testing
        """
        try:
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluate
            train_score = self.model.score(X_train_scaled, y_train)
            test_score = self.model.score(X_test_scaled, y_test)
            
            logger.info(f"Model training completed. Train R²: {train_score:.4f}, Test R²: {test_score:.4f}")
            
            # Save model
            self.save_model()
            
            return {
                'train_score': float(train_score),
                'test_score': float(test_score)
            }
        except Exception as e:
            logger.error(f"Error training model: {e}")
            raise
    
    def save_model(self):
        """Save model and scaler to disk."""
        try:
            with open(self.model_path, 'wb') as f:
                pickle.dump(self.model, f)
            with open(self.scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)
            logger.info(f"Saved model to {self.model_path}")
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            raise
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance from trained model.
        
        Returns:
            Dictionary mapping feature names to importance scores
        """
        if self.model is None or not hasattr(self.model, 'feature_importances_'):
            return {}
        
        importances = self.model.feature_importances_
        return dict(zip(self.feature_names, importances.tolist()))

