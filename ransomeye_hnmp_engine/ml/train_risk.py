# Path and File Name : /home/ransomeye/rebuild/ransomeye_hnmp_engine/ml/train_risk.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Training script for risk model with synthetic data generation

import os
import sys
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ransomeye_hnmp_engine.ml.risk_model import RiskModel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_synthetic_training_data(n_samples: int = 1000):
    """
    Generate synthetic training data for risk model.
    
    Args:
        n_samples: Number of samples to generate
        
        Returns:
            Tuple of (X, y) where X is features (numpy array) and y is risk factors (numpy array)
    """
    np.random.seed(42)
    
    # Generate features
    num_failed_high = np.random.poisson(2, n_samples)
    num_open_ports = np.random.poisson(5, n_samples)
    kernel_age_days = np.random.gamma(2, 180, n_samples).astype(int)  # Mean ~360 days
    num_failed_critical = np.random.poisson(0.5, n_samples)
    num_packages = np.random.normal(500, 200, n_samples).astype(int)
    num_services = np.random.poisson(10, n_samples)
    
    X = np.column_stack([
        num_failed_high,
        num_open_ports,
        kernel_age_days,
        num_failed_critical,
        num_packages,
        num_services
    ])
    
    # Generate risk factors based on features (simulated ground truth)
    # Higher risk for more failures, more ports, older kernels
    y = (
        0.2 * (num_failed_critical / 5.0) +
        0.15 * (num_failed_high / 10.0) +
        0.15 * (num_open_ports / 20.0) +
        0.2 * np.clip(kernel_age_days / 730.0, 0, 1) +  # Normalize to 2 years
        0.1 * np.random.random(n_samples)  # Noise
    )
    
    # Clamp to [0, 1]
    y = np.clip(y, 0.0, 1.0)
    
    return X, y

def main():
    """Main training function."""
    logger.info("Starting risk model training...")
    
    # Initialize model
    model = RiskModel()
    
    # Generate synthetic training data
    logger.info("Generating synthetic training data...")
    X, y = generate_synthetic_training_data(n_samples=1000)
    
    logger.info(f"Generated {len(X)} training samples")
    logger.info(f"Feature shapes: {X.shape}")
    logger.info(f"Risk factor range: [{y.min():.3f}, {y.max():.3f}], Mean: {y.mean():.3f}")
    
    # Train model
    logger.info("Training model...")
    scores = model.train(X, y, test_size=0.2)
    
    logger.info(f"Training completed:")
    logger.info(f"  Train R²: {scores['train_score']:.4f}")
    logger.info(f"  Test R²: {scores['test_score']:.4f}")
    
    # Show feature importance
    importances = model.get_feature_importance()
    logger.info("Feature importance:")
    for feature, importance in sorted(importances.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {feature}: {importance:.4f}")
    
    logger.info("Model saved successfully")

if __name__ == '__main__':
    main()

