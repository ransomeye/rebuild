# Path and File Name : /home/ransomeye/rebuild/ransomeye_linux_agent/models/train/train_detector.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Training script for threat detection model

import os
import sys
import pickle
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_training_data(n_samples: int = 1000):
    """
    Generate synthetic training data.
    
    Args:
        n_samples: Number of samples to generate
        
    Returns:
        Tuple of (X, y) arrays
    """
    np.random.seed(42)
    
    X = []
    y = []
    
    feature_names = [
        'process_count', 'high_cpu_processes', 'high_memory_processes',
        'suspicious_process_names', 'file_count', 'suspicious_extensions',
        'suspicious_paths', 'connection_count', 'established_connections'
    ]
    
    for _ in range(n_samples):
        # Generate features
        if np.random.random() > 0.3:
            # Benign samples
            features = [
                np.random.uniform(10, 100),  # process_count
                np.random.uniform(0, 5),    # high_cpu_processes
                np.random.uniform(0, 3),    # high_memory_processes
                np.random.uniform(0, 1),    # suspicious_process_names
                np.random.uniform(50, 500), # file_count
                np.random.uniform(0, 2),    # suspicious_extensions
                np.random.uniform(0, 5),    # suspicious_paths
                np.random.uniform(5, 50),   # connection_count
                np.random.uniform(3, 40)    # established_connections
            ]
            label = 0
        else:
            # Malicious samples
            features = [
                np.random.uniform(50, 200), # process_count
                np.random.uniform(5, 20),   # high_cpu_processes
                np.random.uniform(3, 15),   # high_memory_processes
                np.random.uniform(2, 10),   # suspicious_process_names
                np.random.uniform(100, 1000), # file_count
                np.random.uniform(5, 50),   # suspicious_extensions
                np.random.uniform(10, 100), # suspicious_paths
                np.random.uniform(20, 200), # connection_count
                np.random.uniform(15, 150)  # established_connections
            ]
            label = 1
        
        X.append(features)
        y.append(label)
    
    return np.array(X), np.array(y)


def train_model(output_path: str = None):
    """
    Train threat detection model.
    
    Args:
        output_path: Path to save trained model
    """
    logger.info("Generating training data...")
    X, y = generate_training_data(n_samples=1000)
    
    logger.info(f"Training data: {len(X)} samples")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    logger.info(f"Training samples: {len(X_train)}, Test samples: {len(X_test)}")
    
    # Train model
    logger.info("Training RandomForest classifier...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    logger.info(f"Model accuracy: {accuracy:.4f}")
    logger.info("\nClassification Report:")
    logger.info(classification_report(y_test, y_pred))
    
    # Save model
    if output_path is None:
        output_path = os.environ.get(
            'MODEL_OUTPUT_PATH',
            '/opt/ransomeye-agent/models/detector_model.pkl'
        )
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    model_data = {
        'model': model,
        'version': '1.0.0',
        'accuracy': float(accuracy),
        'feature_names': [
            'process_count', 'high_cpu_processes', 'high_memory_processes',
            'suspicious_process_names', 'file_count', 'suspicious_extensions',
            'suspicious_paths', 'connection_count', 'established_connections'
        ]
    }
    
    with open(output_file, 'wb') as f:
        pickle.dump(model_data, f)
    
    logger.info(f"Model saved to: {output_path}")


if __name__ == "__main__":
    output_path = sys.argv[1] if len(sys.argv) > 1 else None
    train_model(output_path)

