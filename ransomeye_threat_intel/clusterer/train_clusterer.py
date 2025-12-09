# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/clusterer/train_clusterer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Script to train embeddings if using vector-based clustering

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

# Try to import ML libraries
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import PCA
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("scikit-learn not available")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClustererTrainer:
    """
    Trains embeddings for vector-based clustering.
    """
    
    def __init__(self, model_output_path: Optional[str] = None):
        """
        Initialize trainer.
        
        Args:
            model_output_path: Path to save trained model
        """
        self.model_output_path = model_output_path or os.environ.get(
            'CLUSTERER_MODEL_PATH',
            str(Path(__file__).parent.parent / 'models' / 'clusterer_model.pkl')
        )
        self.vectorizer = None
        self.pca = None
    
    def train(self, iocs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Train clustering model on IOCs.
        
        Args:
            iocs: List of IOC dictionaries
            
        Returns:
            Training metrics
        """
        if not ML_AVAILABLE:
            logger.warning("ML libraries not available")
            return {'status': 'skipped'}
        
        try:
            # Extract text features
            texts = []
            for ioc in iocs:
                # Combine description, tags, and value
                text_parts = [
                    ioc.get('description', ''),
                    ' '.join(ioc.get('tags', [])),
                    ioc.get('value', '')
                ]
                texts.append(' '.join(text_parts))
            
            # Vectorize
            self.vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
            vectors = self.vectorizer.fit_transform(texts).toarray()
            
            # Dimensionality reduction
            if vectors.shape[1] > 50:
                self.pca = PCA(n_components=50)
                vectors = self.pca.fit_transform(vectors)
            
            # Save model
            import pickle
            os.makedirs(os.path.dirname(self.model_output_path), exist_ok=True)
            with open(self.model_output_path, 'wb') as f:
                pickle.dump({
                    'vectorizer': self.vectorizer,
                    'pca': self.pca
                }, f)
            
            logger.info(f"Trained clusterer model: {vectors.shape}")
            return {
                'status': 'success',
                'vector_dim': vectors.shape[1],
                'num_iocs': len(iocs)
            }
            
        except Exception as e:
            logger.error(f"Error training clusterer: {e}")
            return {'status': 'error', 'error': str(e)}


def main():
    """Main training script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Train clustering model')
    parser.add_argument('--iocs-file', type=str, help='JSON file with IOCs')
    parser.add_argument('--output', type=str, help='Output model path')
    
    args = parser.parse_args()
    
    trainer = ClustererTrainer(model_output_path=args.output)
    
    if args.iocs_file:
        with open(args.iocs_file, 'r') as f:
            iocs = json.load(f)
        metrics = trainer.train(iocs)
        print(json.dumps(metrics, indent=2))


if __name__ == '__main__':
    main()

