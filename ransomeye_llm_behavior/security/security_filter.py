# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/security/security_filter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Orchestrator that runs Policy Check (Pre) and Sanitizer (Post)

from typing import Dict, Tuple, Optional, List
import logging

from .policy_engine import PolicyEngine, PolicyViolation
from .sanitizer import PIISanitizer, Redaction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SecurityFilter:
    """
    Orchestrates security filtering: policy check (pre) and sanitization (post).
    """
    
    def __init__(
        self,
        policy_engine: Optional[PolicyEngine] = None,
        sanitizer: Optional[PIISanitizer] = None
    ):
        """
        Initialize security filter.
        
        Args:
            policy_engine: Policy engine instance
            sanitizer: PII sanitizer instance
        """
        self.policy_engine = policy_engine or PolicyEngine()
        self.sanitizer = sanitizer or PIISanitizer()
    
    def filter_input(self, text: str) -> Tuple[bool, Optional[str], List[PolicyViolation]]:
        """
        Filter input text (pre-processing).
        
        Args:
            text: Input text to filter
            
        Returns:
            Tuple of (is_allowed, filtered_text, violations)
        """
        is_allowed, violations = self.policy_engine.check_input(text)
        
        if not is_allowed:
            logger.warning(f"Input blocked due to policy violations: {len(violations)}")
            return False, None, violations
        
        # Input is allowed
        return True, text, []
    
    def filter_output(self, text: str, redact_types: list = None) -> Tuple[str, List[Redaction]]:
        """
        Filter output text (post-processing).
        
        Args:
            text: Output text to sanitize
            redact_types: Types of PII to redact (None = all)
            
        Returns:
            Tuple of (sanitized_text, redactions)
        """
        sanitized, redactions = self.sanitizer.sanitize(text, redact_types=redact_types)
        
        if redactions:
            logger.info(f"Sanitized output: {len(redactions)} redactions")
        
        return sanitized, redactions
    
    def filter_pipeline(self, input_text: str, output_text: str) -> Dict:
        """
        Run complete security filter pipeline.
        
        Args:
            input_text: Input text
            output_text: Output text from LLM
            
        Returns:
            Dictionary with filtering results
        """
        # Pre-filter (policy check)
        input_allowed, filtered_input, input_violations = self.filter_input(input_text)
        
        if not input_allowed:
            return {
                'input_allowed': False,
                'input_violations': [
                    {
                        'type': v.violation_type,
                        'pattern': v.matched_pattern,
                        'severity': v.severity,
                        'context': v.context
                    }
                    for v in input_violations
                ],
                'output_sanitized': None,
                'output_redactions': []
            }
        
        # Post-filter (sanitization)
        sanitized_output, output_redactions = self.filter_output(output_text)
        
        return {
            'input_allowed': True,
            'input_violations': [],
            'output_sanitized': sanitized_output,
            'output_redactions': [
                {
                    'type': r.redaction_type,
                    'position': r.position,
                    'original_length': len(r.original)
                }
                for r in output_redactions
            ],
            'num_redactions': len(output_redactions)
        }

