# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant_advanced/playbook/playbook_matcher.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: ML-based playbook matcher using RandomForestClassifier to map incident summaries to playbook IDs

import os
import pickle
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
import numpy as np

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import Pipeline
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn not available - using rule-based matching")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlaybookMatcher:
    """ML-based playbook matcher."""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize playbook matcher.
        
        Args:
            model_path: Path to trained model (optional)
        """
        self.model_path = model_path or os.environ.get('PLAYBOOK_MODEL_PATH', None)
        self.model = None
        self.vectorizer = None
        self.playbooks = []
        self.playbook_map = {}  # id -> name
        self.ready = False
        
        if SKLEARN_AVAILABLE:
            self._load_or_create_model()
        else:
            logger.warning("scikit-learn not available - using rule-based matching")
            self.ready = True
    
    def _load_or_create_model(self):
        """Load existing model or create new one."""
        if self.model_path and Path(self.model_path).exists():
            try:
                with open(self.model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.model = data['model']
                    self.vectorizer = data['vectorizer']
                    self.playbook_map = data.get('playbook_map', {})
                logger.info(f"Loaded playbook matcher model from {self.model_path}")
                self.ready = True
            except Exception as e:
                logger.error(f"Error loading model: {e}")
                self._create_default_model()
        else:
            self._create_default_model()
    
    def _create_default_model(self):
        """Create a default model with basic training data."""
        if not SKLEARN_AVAILABLE:
            return
        
        try:
            # Default training examples (in production, this would come from feedback data)
            training_data = [
                ("ransomware detected encrypt files", 1),  # Isolate Host
                ("network breach lateral movement", 2),  # Contain Network
                ("suspicious activity investigation", 3),  # Collect Evidence
                ("incident reported notify team", 4),  # Notify Stakeholders
                ("host compromised isolate immediately", 1),
                ("malware spread network segment", 2),
                ("forensic analysis required", 3),
                ("security incident escalation", 4),
            ]
            
            texts = [item[0] for item in training_data]
            labels = [item[1] for item in training_data]
            
            # Create pipeline
            self.vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
            X = self.vectorizer.fit_transform(texts)
            
            self.model = RandomForestClassifier(n_estimators=10, random_state=42)
            self.model.fit(X, labels)
            
            self.ready = True
            logger.info("Created default playbook matcher model")
            
            # Save model if path provided
            if self.model_path:
                self._save_model()
                
        except Exception as e:
            logger.error(f"Error creating default model: {e}")
            self.ready = False
    
    def _save_model(self):
        """Save model to disk."""
        if not self.model_path:
            return
        
        try:
            Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'vectorizer': self.vectorizer,
                    'playbook_map': self.playbook_map
                }, f)
            logger.info(f"Saved playbook matcher model to {self.model_path}")
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def update_playbooks(self, playbooks: List[Dict[str, Any]]):
        """
        Update available playbooks.
        
        Args:
            playbooks: List of playbook dictionaries
        """
        self.playbooks = playbooks
        self.playbook_map = {pb['id']: pb.get('name', f"Playbook {pb['id']}") for pb in playbooks}
        logger.info(f"Updated playbook map with {len(playbooks)} playbooks")
    
    def match(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Match text to playbook.
        
        Args:
            text: Incident summary text
            context: Optional context dictionary
            
        Returns:
            Dictionary with playbook_id, playbook_name, confidence, and reasoning
        """
        # Combine text and context
        full_text = text
        if context:
            if context.get('detected_objects'):
                full_text += " " + " ".join(context['detected_objects'])
        
        if self.model and self.vectorizer and SKLEARN_AVAILABLE:
            # Use ML model
            X = self.vectorizer.transform([full_text])
            probabilities = self.model.predict_proba(X)[0]
            predicted_id = self.model.predict(X)[0]
            confidence = float(max(probabilities))
            
            # Get playbook name
            playbook_name = self.playbook_map.get(predicted_id, f"Playbook {predicted_id}")
            
            # Generate reasoning
            reasoning = self._generate_reasoning(full_text, predicted_id, confidence)
            
        else:
            # Fallback to rule-based matching
            result = self._rule_based_match(full_text)
            predicted_id = result['playbook_id']
            confidence = result['confidence']
            playbook_name = result['playbook_name']
            reasoning = result['reasoning']
        
        return {
            'playbook_id': int(predicted_id),
            'playbook_name': playbook_name,
            'confidence': float(confidence),
            'reasoning': reasoning
        }
    
    def _rule_based_match(self, text: str) -> Dict[str, Any]:
        """
        Rule-based playbook matching (fallback).
        
        Args:
            text: Incident summary text
            
        Returns:
            Match result
        """
        text_lower = text.lower()
        
        # Rule-based patterns
        patterns = {
            1: {  # Isolate Host
                'keywords': ['isolate', 'quarantine', 'compromised', 'infected', 'ransomware', 'malware'],
                'name': 'Isolate Host'
            },
            2: {  # Contain Network
                'keywords': ['network', 'lateral', 'spread', 'breach', 'intrusion'],
                'name': 'Contain Network'
            },
            3: {  # Collect Evidence
                'keywords': ['evidence', 'forensic', 'investigate', 'analyze', 'collect'],
                'name': 'Collect Evidence'
            },
            4: {  # Notify Stakeholders
                'keywords': ['notify', 'escalate', 'report', 'alert', 'stakeholder'],
                'name': 'Notify Stakeholders'
            }
        }
        
        scores = {}
        for playbook_id, pattern in patterns.items():
            score = sum(1 for keyword in pattern['keywords'] if keyword in text_lower)
            scores[playbook_id] = score
        
        if scores:
            best_id = max(scores, key=scores.get)
            confidence = min(0.9, 0.5 + scores[best_id] * 0.1)
            reasoning = f"Matched keywords: {', '.join([k for k in patterns[best_id]['keywords'] if k in text_lower])}"
        else:
            best_id = 3  # Default to Collect Evidence
            confidence = 0.3
            reasoning = "No specific pattern matched - defaulting to evidence collection"
        
        return {
            'playbook_id': best_id,
            'playbook_name': patterns[best_id]['name'],
            'confidence': confidence,
            'reasoning': reasoning
        }
    
    def _generate_reasoning(self, text: str, playbook_id: int, confidence: float) -> str:
        """
        Generate human-readable reasoning for playbook suggestion.
        
        Args:
            text: Input text
            playbook_id: Suggested playbook ID
            confidence: Confidence score
            
        Returns:
            Reasoning string
        """
        playbook_name = self.playbook_map.get(playbook_id, f"Playbook {playbook_id}")
        
        # Extract key terms
        key_terms = text.split()[:5]  # First 5 words
        
        reasoning = f"Suggested '{playbook_name}' (confidence: {confidence:.2f}) based on keywords: {', '.join(key_terms)}"
        
        return reasoning
    
    def is_ready(self) -> bool:
        """Check if matcher is ready."""
        return self.ready

