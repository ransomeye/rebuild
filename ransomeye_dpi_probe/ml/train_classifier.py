# Path and File Name : /home/ransomeye/rebuild/ransomeye_dpi_probe/ml/train_classifier.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Training script for the flow classifier model

import os
import sys
import json
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import pickle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_training_data(data_path: str) -> tuple:
    """
    Load training data from JSON file.
    
    Expected format: List of dictionaries with 'features' and 'label' keys.
    
    Args:
        data_path: Path to training data JSON file
        
    Returns:
        Tuple of (X, y) arrays
    """
    with open(data_path, 'r') as f:
        data = json.load(f)
    
    # Extract features and labels
    features = []
    labels = []
    
    for item in data:
        if 'features' in item and 'label' in item:
            features.append(item['features'])
            labels.append(item['label'])
    
    X = np.array(features)
    y = np.array(labels)
    
    # Encode labels if strings
    if isinstance(y[0], str):
        le = LabelEncoder()
        y = le.fit_transform(y)
        logger.info(f"Label encoding: {le.classes_}")
    
    logger.info(f"Loaded {len(X)} samples with {X.shape[1]} features")
    return X, y


def generate_synthetic_data(n_samples: int = 1000) -> tuple:
    """
    Generate synthetic training data for testing.
    
    Args:
        n_samples: Number of samples to generate
        
    Returns:
        Tuple of (X, y) arrays
    """
    logger.info(f"Generating {n_samples} synthetic training samples")
    
    np.random.seed(42)
    n_features = 26  # Match AssetClassifier.FEATURE_NAMES
    
    X = np.random.rand(n_samples, n_features)
    
    # Create some patterns for different classes
    y = np.zeros(n_samples, dtype=int)
    
    # C2 beaconing: low packet count, periodic
    c2_indices = np.random.choice(n_samples, size=n_samples // 5, replace=False)
    X[c2_indices, 0] = np.random.randint(5, 50, size=len(c2_indices))  # packet_count
    X[c2_indices, 5] = np.random.uniform(0.1, 1.0, size=len(c2_indices))  # packets_per_second (low)
    y[c2_indices] = 1  # c2_beaconing
    
    # Data exfiltration: high bytes, long duration
    exfil_indices = np.random.choice(n_samples, size=n_samples // 5, replace=False)
    exfil_indices = np.setdiff1d(exfil_indices, c2_indices)
    X[exfil_indices, 1] = np.random.randint(1000000, 10000000, size=len(exfil_indices))  # total_bytes
    X[exfil_indices, 2] = np.random.uniform(60, 3600, size=len(exfil_indices))  # duration
    y[exfil_indices] = 2  # data_exfiltration
    
    # Port scan: many connections, short duration
    scan_indices = np.random.choice(n_samples, size=n_samples // 10, replace=False)
    scan_indices = np.setdiff1d(scan_indices, np.concatenate([c2_indices, exfil_indices]))
    X[scan_indices, 0] = np.random.randint(100, 1000, size=len(scan_indices))
    X[scan_indices, 2] = np.random.uniform(0.1, 5.0, size=len(scan_indices))
    y[scan_indices] = 3  # port_scan
    
    # Malicious: combination of suspicious features
    malicious_indices = np.random.choice(n_samples, size=n_samples // 10, replace=False)
    malicious_indices = np.setdiff1d(malicious_indices, 
                                    np.concatenate([c2_indices, exfil_indices, scan_indices]))
    X[malicious_indices, 12] = 1.0  # RST flag
    X[malicious_indices, 19] = np.random.uniform(7.0, 8.0, size=len(malicious_indices))  # High entropy
    y[malicious_indices] = 4  # malicious
    
    # Rest are normal (class 0)
    
    return X, y


def train_model(X: np.ndarray, y: np.ndarray, model_dir: str, test_size: float = 0.2):
    """
    Train classifier model.
    
    Args:
        X: Feature matrix
        y: Labels
        model_dir: Directory to save model
        test_size: Test set size ratio
    """
    logger.info("Starting model training...")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    
    logger.info(f"Training set: {len(X_train)} samples")
    logger.info(f"Test set: {len(X_test)} samples")
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train model
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=25,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
        class_weight='balanced'
    )
    
    logger.info("Training Random Forest classifier...")
    model.fit(X_train_scaled, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)
    
    logger.info(f"Test accuracy: {accuracy:.4f}")
    logger.info("\nClassification Report:")
    logger.info(classification_report(y_test, y_pred))
    
    logger.info("\nConfusion Matrix:")
    logger.info(confusion_matrix(y_test, y_pred))
    
    # Save model
    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    
    model_file = model_dir / 'asset_classifier.pkl'
    scaler_file = model_dir / 'asset_classifier_scaler.pkl'
    
    with open(model_file, 'wb') as f:
        pickle.dump(model, f)
    with open(scaler_file, 'wb') as f:
        pickle.dump(scaler, f)
    
    logger.info(f"Model saved to {model_file}")
    logger.info(f"Scaler saved to {scaler_file}")
    
    # Save metadata
    metadata = {
        'n_features': X.shape[1],
        'n_classes': len(np.unique(y)),
        'test_accuracy': float(accuracy),
        'n_estimators': 200,
        'max_depth': 25
    }
    
    metadata_file = model_dir / 'asset_classifier_metadata.json'
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"Metadata saved to {metadata_file}")


def main():
    """Main training entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Train flow classifier')
    parser.add_argument('--data', type=str, help='Path to training data JSON')
    parser.add_argument('--model-dir', type=str, 
                       default=os.environ.get('MODEL_DIR', '/home/ransomeye/rebuild/models'),
                       help='Model output directory')
    parser.add_argument('--synthetic', action='store_true',
                       help='Generate synthetic training data')
    parser.add_argument('--samples', type=int, default=1000,
                       help='Number of synthetic samples')
    
    args = parser.parse_args()
    
    if args.synthetic or not args.data:
        logger.info("Generating synthetic training data...")
        X, y = generate_synthetic_data(n_samples=args.samples)
    else:
        if not Path(args.data).exists():
            logger.error(f"Training data file not found: {args.data}")
            sys.exit(1)
        X, y = load_training_data(args.data)
    
    train_model(X, y, args.model_dir)


if __name__ == '__main__':
    main()

