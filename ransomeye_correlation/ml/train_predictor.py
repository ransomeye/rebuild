# Path and File Name : /home/ransomeye/rebuild/ransomeye_correlation/ml/train_predictor.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Script to train RandomForestRegressor on synthetic data and save .pkl model

import os
import sys
import pickle
import numpy as np
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import scikit-learn
try:
    from sklearn.ensemble import RandomForestRegressor
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.error("scikit-learn not available, cannot train model")
    sys.exit(1)

def generate_synthetic_data(n_samples: int = 1000) -> tuple:
    """
    Generate synthetic training data.
    
    Args:
        n_samples: Number of samples to generate
        
    Returns:
        Tuple of (X, y) where X is features and y is labels
    """
    np.random.seed(42)
    
    # Generate features
    num_hosts = np.random.randint(1, 50, n_samples)
    alert_severity_sum = np.random.randint(1, 200, n_samples)
    distinct_users = np.random.randint(1, 20, n_samples)
    time_span = np.random.uniform(0.1, 48.0, n_samples)
    
    X = np.column_stack([num_hosts, alert_severity_sum, distinct_users, time_span])
    
    # Generate labels (confidence scores)
    # Higher scores for more hosts, more alerts, more users, longer time span
    y = (
        num_hosts * 0.01 +
        alert_severity_sum * 0.002 +
        distinct_users * 0.02 +
        time_span * 0.01 +
        np.random.normal(0, 0.1, n_samples)
    )
    y = np.clip(y, 0.0, 1.0)
    
    return X, y

def train_model(output_path: Path):
    """
    Train confidence predictor model.
    
    Args:
        output_path: Path to save model
    """
    logger.info("Generating synthetic training data...")
    X, y = generate_synthetic_data(n_samples=1000)
    
    logger.info(f"Training RandomForestRegressor on {len(X)} samples...")
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X, y)
    
    # Save model
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'wb') as f:
        pickle.dump(model, f)
    
    logger.info(f"Model trained and saved to: {output_path}")
    
    # Print feature importance
    feature_names = ['num_hosts', 'alert_severity_sum', 'distinct_users', 'time_span']
    importances = model.feature_importances_
    logger.info("Feature importances:")
    for name, importance in zip(feature_names, importances):
        logger.info(f"  {name}: {importance:.4f}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Train confidence predictor model')
    parser.add_argument('--output', type=str,
                       default=os.path.join(os.environ.get('CORRELATION_DATA_DIR', '/home/ransomeye/rebuild/ransomeye_correlation/data'), 'confidence_model.pkl'),
                       help='Output model path')
    
    args = parser.parse_args()
    
    try:
        train_model(Path(args.output))
        return 0
    except Exception as e:
        logger.error(f"Error training model: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main())

