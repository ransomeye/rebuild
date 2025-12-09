# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/governor/validator.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Validator that uses a local model to score "Hallucination Risk"

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import logging

# Try to import ML libraries
try:
    import pickle
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("ML libraries not available, using rule-based validation")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HallucinationValidator:
    """
    Validator that scores hallucination risk.
    Uses a local model to compare answer against context.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize validator.
        
        Args:
            model_path: Path to trained validator model
        """
        self.model_path = model_path or os.environ.get('VALIDATOR_MODEL_PATH')
        self.model = None
        self.vectorizer = None
        self._load_model()
    
    def _load_model(self):
        """Load validator model if available."""
        if self.model_path and os.path.exists(self.model_path) and ML_AVAILABLE:
            try:
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    if isinstance(model_data, dict):
                        self.model = model_data.get('model')
                        self.vectorizer = model_data.get('vectorizer')
                    else:
                        self.model = model_data
                logger.info(f"Loaded validator model from {self.model_path}")
            except Exception as e:
                logger.warning(f"Could not load validator model: {e}")
        
        # Initialize vectorizer if not loaded
        if not self.vectorizer and ML_AVAILABLE:
            self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
    
    def validate(
        self,
        answer: str,
        context: str,
        threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Validate answer against context.
        
        Args:
            answer: Answer text to validate
            context: Context text to compare against
            threshold: Confidence threshold (0-1)
            
        Returns:
            Dictionary with validation results
        """
        if not answer or not context:
            return {
                'is_valid': False,
                'confidence': 0.0,
                'risk_score': 1.0,
                'method': 'empty_input',
                'issues': ['Empty answer or context']
            }
        
        # Use model if available
        if self.model and ML_AVAILABLE:
            try:
                return self._model_validate(answer, context, threshold)
            except Exception as e:
                logger.warning(f"Model validation error: {e}, using rule-based")
        
        # Fallback to rule-based
        return self._rule_based_validate(answer, context, threshold)
    
    def _model_validate(
        self,
        answer: str,
        context: str,
        threshold: float
    ) -> Dict[str, Any]:
        """Validate using trained model."""
        try:
            # Prepare features
            if self.vectorizer:
                # Fit vectorizer if needed
                try:
                    features = self.vectorizer.transform([answer, context])
                    answer_vec = features[0]
                    context_vec = features[1]
                except:
                    # Fit on both texts
                    self.vectorizer.fit([answer, context])
                    features = self.vectorizer.transform([answer, context])
                    answer_vec = features[0]
                    context_vec = features[1]
                
                # Calculate similarity
                similarity = cosine_similarity([answer_vec], [context_vec])[0][0]
            else:
                similarity = self._text_similarity(answer, context)
            
            # Use model to predict
            if hasattr(self.model, 'predict_proba'):
                # Create feature vector
                features = np.array([[similarity, len(answer), len(context)]])
                proba = self.model.predict_proba(features)[0]
                confidence = float(proba[1])  # Probability of valid
            elif hasattr(self.model, 'predict'):
                features = np.array([[similarity, len(answer), len(context)]])
                prediction = self.model.predict(features)[0]
                confidence = float(prediction) if isinstance(prediction, (int, float)) else 0.5
            else:
                # Use similarity as confidence
                confidence = float(similarity)
            
            is_valid = confidence >= threshold
            risk_score = 1.0 - confidence
            
            return {
                'is_valid': is_valid,
                'confidence': confidence,
                'risk_score': risk_score,
                'method': 'model',
                'similarity': float(similarity),
                'issues': [] if is_valid else [f'Low confidence: {confidence:.2f}']
            }
            
        except Exception as e:
            logger.error(f"Error in model validation: {e}")
            return self._rule_based_validate(answer, context, threshold)
    
    def _rule_based_validate(
        self,
        answer: str,
        context: str,
        threshold: float
    ) -> Dict[str, Any]:
        """Rule-based validation fallback."""
        # Calculate text similarity
        similarity = self._text_similarity(answer, context)
        
        # Additional checks
        issues = []
        
        # Check for contradictory statements
        answer_lower = answer.lower()
        context_lower = context.lower()
        
        contradictions = [
            ('not found', 'found'),
            ('no evidence', 'evidence'),
            ('impossible', 'possible'),
            ('never', 'occurred')
        ]
        
        for neg, pos in contradictions:
            if neg in answer_lower and pos in context_lower:
                issues.append(f"Contradiction: '{neg}' vs '{pos}'")
        
        # Check for unsupported claims
        strong_claims = ['definitely', 'certainly', 'proven', 'confirmed']
        if any(claim in answer_lower for claim in strong_claims):
            if similarity < 0.6:
                issues.append("Strong claims with low context similarity")
        
        # Calculate confidence
        confidence = similarity
        if issues:
            confidence *= 0.7  # Reduce confidence if issues found
        
        is_valid = confidence >= threshold
        risk_score = 1.0 - confidence
        
        return {
            'is_valid': is_valid,
            'confidence': float(confidence),
            'risk_score': float(risk_score),
            'method': 'rule_based',
            'similarity': float(similarity),
            'issues': issues
        }
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity."""
        # Tokenize
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Remove stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words1 = words1 - stop_words
        words2 = words2 - stop_words
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        if union == 0:
            return 0.0
        
        jaccard = intersection / union
        
        # Also check substring overlap
        text1_lower = text1.lower()
        text2_lower = text2.lower()
        
        # Count common n-grams
        n = 3
        ngrams1 = set()
        ngrams2 = set()
        
        for i in range(len(text1_lower) - n + 1):
            ngrams1.add(text1_lower[i:i+n])
        for i in range(len(text2_lower) - n + 1):
            ngrams2.add(text2_lower[i:i+n])
        
        if ngrams1 and ngrams2:
            ngram_sim = len(ngrams1 & ngrams2) / len(ngrams1 | ngrams2)
        else:
            ngram_sim = 0.0
        
        # Combine similarities
        combined = (jaccard * 0.6) + (ngram_sim * 0.4)
        return min(combined, 1.0)

