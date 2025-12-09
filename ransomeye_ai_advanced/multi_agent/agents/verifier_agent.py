# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/multi_agent/agents/verifier_agent.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Verifier agent that compares Reasoner's output against Context and triggers correction if facts don't align

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from .base_agent import BaseAgent, AgentState
from ..message_bus import Message

# Try to import validator model
try:
    import pickle
    import numpy as np
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VerifierAgent(BaseAgent):
    """
    Verifier agent that validates answers against context.
    Checks for hallucinations and fact alignment.
    """
    
    def __init__(
        self,
        agent_name: str,
        message_bus,
        validator_model_path: Optional[str] = None
    ):
        """
        Initialize verifier agent.
        
        Args:
            agent_name: Agent name
            message_bus: Message bus instance
            validator_model_path: Path to trained validator model
        """
        super().__init__(
            agent_name=agent_name,
            message_bus=message_bus,
            description="Verifies answers against context to detect hallucinations"
        )
        self.validator_model_path = validator_model_path or os.environ.get('VALIDATOR_MODEL_PATH')
        self.validator_model = None
        self._load_validator()
    
    def _load_validator(self):
        """Load validator model if available."""
        if self.validator_model_path and os.path.exists(self.validator_model_path):
            try:
                with open(self.validator_model_path, 'rb') as f:
                    self.validator_model = pickle.load(f)
                logger.info(f"Loaded validator model from {self.validator_model_path}")
            except Exception as e:
                logger.warning(f"Could not load validator model: {e}")
    
    async def process(
        self,
        message: Message,
        state: AgentState
    ) -> tuple[Optional[Message], AgentState]:
        """
        Process verification request.
        
        Args:
            message: Incoming message with answer to verify
            state: Current conversation state
            
        Returns:
            Tuple of (output_message, updated_state)
        """
        try:
            answer = message.payload.get('answer', state.context.get('reasoned_answer', ''))
            context = message.payload.get('context', state.context.get('retrieved_context', []))
            
            # Verify answer against context
            verification_result = await self._verify(answer, context)
            
            # Update state
            state.context['verification'] = verification_result
            state.intermediate_results['verifier_output'] = verification_result
            
            # If verification fails, mark for correction
            if not verification_result.get('is_valid', False):
                state.metadata['needs_correction'] = True
                state.metadata['verification_issues'] = verification_result.get('issues', [])
            
            # Create response message
            response_message = Message(
                sender=self.agent_name,
                receiver="orchestrator",
                message_type="verification_result",
                payload={
                    'verification': verification_result,
                    'answer': answer
                },
                correlation_id=message.correlation_id or message.message_id
            )
            
            logger.info(f"Verifier completed: valid={verification_result.get('is_valid', False)}")
            return response_message, state
            
        except Exception as e:
            logger.error(f"Error in verifier agent: {e}")
            state.metadata['verifier_error'] = str(e)
            # Default to valid on error (fail open)
            state.context['verification'] = {'is_valid': True, 'confidence': 0.5, 'method': 'error_fallback'}
            return None, state
    
    async def _verify(
        self,
        answer: str,
        context: List[Any]
    ) -> Dict[str, Any]:
        """
        Verify answer against context.
        
        Args:
            answer: Answer to verify
            context: Retrieved context
            
        Returns:
            Verification result dictionary
        """
        if not answer:
            return {
                'is_valid': False,
                'confidence': 0.0,
                'method': 'empty_answer',
                'issues': ['Answer is empty']
            }
        
        if not context:
            return {
                'is_valid': True,  # Can't verify without context
                'confidence': 0.5,
                'method': 'no_context',
                'issues': []
            }
        
        # Extract text from context
        context_texts = []
        for item in context:
            if hasattr(item, 'text'):
                context_texts.append(item.text)
            elif isinstance(item, dict):
                context_texts.append(item.get('text', ''))
            else:
                context_texts.append(str(item))
        
        combined_context = ' '.join(context_texts)
        
        # Method 1: Use validator model if available
        if self.validator_model:
            try:
                score = self._validator_model_score(answer, combined_context)
                is_valid = score > 0.5
                return {
                    'is_valid': is_valid,
                    'confidence': float(score),
                    'method': 'validator_model',
                    'issues': [] if is_valid else ['Low confidence score from validator model']
                }
            except Exception as e:
                logger.warning(f"Validator model error: {e}, falling back to rule-based")
        
        # Method 2: Rule-based verification
        return self._rule_based_verify(answer, combined_context)
    
    def _validator_model_score(self, answer: str, context: str) -> float:
        """
        Score answer using validator model.
        
        Args:
            answer: Answer text
            context: Context text
            
        Returns:
            Score between 0 and 1
        """
        # Simple feature extraction (can be enhanced)
        answer_lower = answer.lower()
        context_lower = context.lower()
        
        # Extract key terms from answer
        answer_terms = set(answer_lower.split())
        context_terms = set(context_lower.split())
        
        # Calculate overlap
        if len(answer_terms) == 0:
            return 0.0
        
        overlap = len(answer_terms & context_terms) / len(answer_terms)
        
        # If model is a scikit-learn model, use it
        if hasattr(self.validator_model, 'predict_proba'):
            try:
                # Create feature vector (simplified)
                features = np.array([[overlap, len(answer), len(context)]])
                proba = self.validator_model.predict_proba(features)[0]
                return float(proba[1])  # Probability of valid
            except Exception:
                pass
        
        # Fallback: use overlap as score
        return min(overlap * 1.5, 1.0)  # Scale overlap
    
    def _rule_based_verify(
        self,
        answer: str,
        context: str
    ) -> Dict[str, Any]:
        """
        Rule-based verification.
        
        Args:
            answer: Answer text
            context: Context text
            
        Returns:
            Verification result
        """
        issues = []
        answer_lower = answer.lower()
        context_lower = context.lower()
        
        # Check 1: Key terms overlap
        answer_words = set(answer_lower.split())
        context_words = set(context_lower.split())
        
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
        answer_words = answer_words - stop_words
        context_words = context_words - stop_words
        
        if len(answer_words) > 0:
            overlap_ratio = len(answer_words & context_words) / len(answer_words)
        else:
            overlap_ratio = 0.0
        
        if overlap_ratio < 0.3:
            issues.append(f"Low term overlap ({overlap_ratio:.2f})")
        
        # Check 2: Check for contradictory phrases
        contradictions = [
            ('not found', 'found'),
            ('no evidence', 'evidence shows'),
            ('impossible', 'possible'),
            ('never happened', 'occurred')
        ]
        
        for neg, pos in contradictions:
            if neg in answer_lower and pos in context_lower:
                issues.append(f"Potential contradiction: '{neg}' vs '{pos}'")
        
        # Check 3: Check for unsupported claims
        claim_indicators = ['definitely', 'certainly', 'proven', 'confirmed']
        if any(indicator in answer_lower for indicator in claim_indicators):
            if overlap_ratio < 0.5:
                issues.append("Strong claims with insufficient context support")
        
        # Determine validity
        is_valid = len(issues) == 0 or overlap_ratio > 0.4
        confidence = min(overlap_ratio * 1.2, 1.0) if is_valid else max(overlap_ratio, 0.2)
        
        return {
            'is_valid': is_valid,
            'confidence': float(confidence),
            'method': 'rule_based',
            'issues': issues,
            'overlap_ratio': float(overlap_ratio)
        }

