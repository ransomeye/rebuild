# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant/retriever/ranker_model.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Trainable re-ranker with SHAP explanations

import os
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import scikit-learn and SHAP
try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import LinearRegression
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available, ranker will use simple scoring")

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("SHAP not available, explanations will not be generated")

class RankerModel:
    """
    Trainable re-ranker that outputs relevance scores with SHAP explanations.
    """
    
    def __init__(self, model_path: str = None):
        """
        Initialize ranker model.
        
        Args:
            model_path: Path to saved model file
        """
        self.model_path = Path(model_path or os.environ.get(
            'RANKER_MODEL_PATH',
            os.path.join(os.environ.get('ASSISTANT_DATA_DIR', '/home/ransomeye/rebuild/ransomeye_assistant/data'), 'ranker_model.pkl')
        ))
        self.model = None
        self.model_loaded = False
        
        if self.model_path and self.model_path.exists():
            self._load_model()
        else:
            self._create_default_model()
    
    def _create_default_model(self):
        """Create default ranker model."""
        if SKLEARN_AVAILABLE:
            # Use RandomForest for better feature importance
            self.model = RandomForestRegressor(n_estimators=10, random_state=42)
            # Initialize with dummy data
            X_dummy = np.random.rand(10, 5)
            y_dummy = np.random.rand(10)
            self.model.fit(X_dummy, y_dummy)
            logger.info("Created default ranker model (RandomForest)")
        else:
            self.model = None
            logger.warning("Using simple scoring (no ML model)")
    
    def _load_model(self):
        """Load saved model."""
        try:
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
            self.model_loaded = True
            logger.info(f"Loaded ranker model from: {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}, using default")
            self._create_default_model()
    
    def _extract_features(self, query: str, document: Dict[str, Any]) -> np.ndarray:
        """
        Extract features from query-document pair.
        
        Args:
            query: Query text
            document: Document dictionary
            
        Returns:
            Feature vector
        """
        doc_text = document.get('text', '')
        
        # Simple features
        features = []
        
        # 1. Query length
        features.append(len(query.split()))
        
        # 2. Document length
        features.append(len(doc_text.split()))
        
        # 3. Word overlap ratio
        query_words = set(query.lower().split())
        doc_words = set(doc_text.lower().split())
        overlap = len(query_words & doc_words)
        total_unique = len(query_words | doc_words)
        overlap_ratio = overlap / total_unique if total_unique > 0 else 0
        features.append(overlap_ratio)
        
        # 4. Query term frequency in document
        query_terms_in_doc = sum(1 for word in query_words if word in doc_words)
        features.append(query_terms_in_doc)
        
        # 5. Distance from vector search (if available)
        distance = document.get('distance', 0.0)
        features.append(float(distance))
        
        return np.array(features).reshape(1, -1)
    
    def rank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Rank candidates by relevance.
        
        Args:
            query: Query text
            candidates: List of candidate documents
            top_k: Number of top results to return
            
        Returns:
            List of ranked results with scores
        """
        if not candidates:
            return []
        
        scored_candidates = []
        
        for candidate in candidates:
            # Extract features
            features = self._extract_features(query, candidate)
            
            # Score using model
            if self.model and SKLEARN_AVAILABLE:
                score = self.model.predict(features)[0]
            else:
                # Simple scoring based on features
                score = features[0][2] * 10 - features[0][4]  # overlap_ratio * 10 - distance
            
            scored_candidates.append({
                'document': candidate,
                'score': float(score),
                'features': features[0].tolist()
            })
        
        # Sort by score (descending)
        scored_candidates.sort(key=lambda x: x['score'], reverse=True)
        
        # Return top_k
        return scored_candidates[:top_k]
    
    def get_shap_explanations(self, query: str, document: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate SHAP explanations for ranking decision.
        
        Args:
            query: Query text
            document: Document dictionary
            
        Returns:
            SHAP explanation dictionary or None
        """
        if not SHAP_AVAILABLE or not self.model or not SKLEARN_AVAILABLE:
            return None
        
        try:
            # Extract features
            features = self._extract_features(query, document)
            
            # Create SHAP explainer
            explainer = shap.TreeExplainer(self.model) if hasattr(self.model, 'tree_') else shap.LinearExplainer(self.model, features)
            
            # Calculate SHAP values
            shap_values = explainer.shap_values(features)
            
            # Feature names
            feature_names = [
                'query_length',
                'doc_length',
                'word_overlap_ratio',
                'query_terms_in_doc',
                'vector_distance'
            ]
            
            # Format SHAP values
            if isinstance(shap_values, list):
                shap_values = shap_values[0]
            
            shap_dict = {}
            for name, value in zip(feature_names, shap_values[0]):
                shap_dict[name] = float(value)
            
            return {
                'shap_values': shap_dict,
                'base_value': float(explainer.expected_value) if hasattr(explainer, 'expected_value') else 0.0
            }
            
        except Exception as e:
            logger.error(f"Error generating SHAP explanations: {e}")
            return None
    
    def train(self, training_data: List[Dict[str, Any]]):
        """
        Train the ranker model on feedback data.
        
        Args:
            training_data: List of training examples with (query, document, relevance_score)
        """
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn not available, cannot train model")
            return
        
        if not training_data:
            logger.warning("No training data provided")
            return
        
        # Extract features and labels
        X = []
        y = []
        
        for example in training_data:
            query = example['query']
            document = example['document']
            relevance = example.get('relevance_score', 0.0)
            
            features = self._extract_features(query, document)
            X.append(features[0])
            y.append(relevance)
        
        X = np.array(X)
        y = np.array(y)
        
        # Train model
        if self.model is None:
            self.model = RandomForestRegressor(n_estimators=10, random_state=42)
        
        self.model.fit(X, y)
        
        # Save model
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)
        
        logger.info(f"Trained ranker model on {len(training_data)} examples")

