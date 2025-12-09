# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant_advanced/explain/shap_integration.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: SHAP integration for explaining playbook suggestions

import os
from typing import Dict, Any, Optional
import logging
import numpy as np

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logging.warning("SHAP not available - explainability disabled")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SHAPIntegration:
    """SHAP explainability for playbook suggestions."""
    
    def __init__(self):
        """Initialize SHAP integration."""
        self.available = SHAP_AVAILABLE
    
    def explain_playbook_suggestion(
        self,
        summary: str,
        context: Optional[Dict[str, Any]],
        suggested_playbook_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Generate SHAP explanations for playbook suggestion.
        
        Args:
            summary: Incident summary
            context: Optional context (OCR text, detected objects)
            suggested_playbook_id: Suggested playbook ID
            
        Returns:
            SHAP explanation dictionary
        """
        if not self.available:
            return self._mock_explanation(summary, context, suggested_playbook_id)
        
        try:
            # Import playbook matcher to get model
            from ..playbook.playbook_matcher import PlaybookMatcher
            
            # This is a simplified explanation - in production, you'd use
            # SHAP TreeExplainer on the RandomForestClassifier
            
            # Extract features
            features = self._extract_features(summary, context)
            
            # Generate explanation (simplified)
            explanation = {
                'summary': summary,
                'suggested_playbook_id': suggested_playbook_id,
                'feature_importance': self._calculate_feature_importance(features),
                'reasoning': self._generate_reasoning(features, suggested_playbook_id)
            }
            
            return explanation
            
        except Exception as e:
            logger.error(f"Error generating SHAP explanation: {e}")
            return self._mock_explanation(summary, context, suggested_playbook_id)
    
    def _extract_features(self, summary: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract features for explanation.
        
        Args:
            summary: Incident summary
            context: Optional context
            
        Returns:
            Feature dictionary
        """
        features = {
            'summary_length': len(summary),
            'has_ransom_keywords': any(kw in summary.lower() for kw in ['ransom', 'encrypt', 'bitcoin']),
            'has_network_keywords': any(kw in summary.lower() for kw in ['network', 'lateral', 'breach']),
            'has_error_keywords': any(kw in summary.lower() for kw in ['error', 'failed', 'denied']),
            'has_ocr_text': context and context.get('ocr_text') is not None,
            'detected_objects_count': len(context.get('detected_objects', [])) if context else 0
        }
        
        if context and context.get('detected_objects'):
            features['has_terminal'] = 'terminal' in context['detected_objects']
            features['has_error_dialog'] = 'error_dialog' in context['detected_objects']
            features['has_ransom_note'] = 'ransom_note' in context['detected_objects']
        
        return features
    
    def _calculate_feature_importance(self, features: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate feature importance (simplified).
        
        Args:
            features: Feature dictionary
            
        Returns:
            Feature importance dictionary
        """
        importance = {}
        
        # Simple heuristic-based importance
        if features.get('has_ransom_keywords') or features.get('has_ransom_note'):
            importance['ransomware_indicator'] = 0.8
        if features.get('has_network_keywords'):
            importance['network_breach_indicator'] = 0.7
        if features.get('has_error_keywords') or features.get('has_error_dialog'):
            importance['error_indicator'] = 0.6
        if features.get('has_terminal'):
            importance['terminal_activity'] = 0.5
        
        # Normalize
        total = sum(importance.values())
        if total > 0:
            importance = {k: v / total for k, v in importance.items()}
        
        return importance
    
    def _generate_reasoning(self, features: Dict[str, Any], playbook_id: int) -> str:
        """
        Generate human-readable reasoning.
        
        Args:
            features: Feature dictionary
            playbook_id: Suggested playbook ID
            
        Returns:
            Reasoning string
        """
        reasons = []
        
        if features.get('has_ransom_keywords') or features.get('has_ransom_note'):
            reasons.append("Detected ransomware indicators (encryption keywords or ransom note)")
        if features.get('has_network_keywords'):
            reasons.append("Network breach or lateral movement detected")
        if features.get('has_terminal'):
            reasons.append("Terminal/command-line activity detected")
        if features.get('has_error_dialog'):
            reasons.append("Error dialogs detected in screenshot")
        
        if reasons:
            return ". ".join(reasons)
        else:
            return "General security incident pattern matched"
    
    def _mock_explanation(self, summary: str, context: Optional[Dict[str, Any]], playbook_id: int) -> Dict[str, Any]:
        """
        Generate mock explanation when SHAP is unavailable.
        
        Args:
            summary: Incident summary
            context: Optional context
            playbook_id: Suggested playbook ID
            
        Returns:
            Mock explanation dictionary
        """
        return {
            'summary': summary,
            'suggested_playbook_id': playbook_id,
            'feature_importance': {
                'text_content': 0.5,
                'context_features': 0.5
            },
            'reasoning': f"Playbook {playbook_id} suggested based on incident summary analysis"
        }

