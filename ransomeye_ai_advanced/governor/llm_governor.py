# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/governor/llm_governor.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Main LLM Governor entry point that enforces rate limits, policy checks, and validation

import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .rate_limiter import RateLimiter
from .policy_engine import PolicyEngine
from .validator import HallucinationValidator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMGovernor:
    """
    Main LLM Governor that enforces:
    1. Rate Limits (token buckets per user/system)
    2. Safety Policy (regex/keyword blocking)
    3. Hallucination Check (validator scores answer against context)
    """
    
    def __init__(
        self,
        qps_limit: Optional[float] = None,
        policy_path: Optional[str] = None,
        validator_model_path: Optional[str] = None
    ):
        """
        Initialize LLM Governor.
        
        Args:
            qps_limit: Queries per second limit
            policy_path: Path to policy.json
            validator_model_path: Path to validator model
        """
        self.rate_limiter = RateLimiter(qps_limit=qps_limit)
        self.policy_engine = PolicyEngine(policy_path=policy_path)
        self.validator = HallucinationValidator(model_path=validator_model_path)
        
        logger.info("LLM Governor initialized")
    
    async def check_request(
        self,
        input_text: str,
        user_id: Optional[str] = None,
        tokens: int = 1
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Check if request is allowed (rate limit + policy).
        
        Args:
            input_text: Input text to check
            user_id: Optional user ID
            tokens: Number of tokens for rate limiting
            
        Returns:
            Tuple of (allowed, error_message, metadata)
        """
        metadata = {}
        
        # Step 1: Rate limit check
        rate_allowed, wait_time = await self.rate_limiter.check_rate_limit(
            user_id=user_id,
            tokens=tokens
        )
        if not rate_allowed:
            error_msg = f"Rate limit exceeded. Please wait {wait_time:.1f} seconds."
            metadata['rate_limit'] = {'wait_time': wait_time}
            return False, error_msg, metadata
        
        metadata['rate_limit'] = {'allowed': True}
        
        # Step 2: Policy check
        policy_allowed, violations = self.policy_engine.check_input(
            text=input_text,
            user_id=user_id
        )
        if not policy_allowed:
            error_msg = f"Policy violation: {', '.join(violations)}"
            metadata['policy'] = {'violations': violations}
            return False, error_msg, metadata
        
        metadata['policy'] = {'allowed': True}
        
        return True, None, metadata
    
    def validate_output(
        self,
        output_text: str,
        context: str,
        user_id: Optional[str] = None,
        threshold: float = 0.5
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate output (policy + hallucination check).
        
        Args:
            output_text: Output text to validate
            context: Context used to generate output
            user_id: Optional user ID
            threshold: Validation confidence threshold
            
        Returns:
            Tuple of (is_valid, validation_result)
        """
        # Step 1: Policy check on output
        policy_allowed, violations = self.policy_engine.check_output(
            text=output_text,
            user_id=user_id
        )
        
        if not policy_allowed:
            return False, {
                'is_valid': False,
                'method': 'policy',
                'violations': violations
            }
        
        # Step 2: Hallucination validation
        validation_result = self.validator.validate(
            answer=output_text,
            context=context,
            threshold=threshold
        )
        
        return validation_result.get('is_valid', False), validation_result
    
    async def govern_llm_call(
        self,
        input_text: str,
        output_text: str,
        context: str,
        user_id: Optional[str] = None,
        tokens: int = 1,
        validation_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Complete governance check for an LLM call.
        
        Args:
            input_text: Input to LLM
            output_text: Output from LLM
            context: Context used
            user_id: Optional user ID
            tokens: Tokens consumed
            validation_threshold: Validation threshold
            
        Returns:
            Complete governance result
        """
        result = {
            'request_allowed': False,
            'output_valid': False,
            'metadata': {}
        }
        
        # Check request
        request_allowed, error_msg, request_metadata = await self.check_request(
            input_text=input_text,
            user_id=user_id,
            tokens=tokens
        )
        
        result['request_allowed'] = request_allowed
        result['metadata']['request'] = request_metadata
        
        if not request_allowed:
            result['error'] = error_msg
            return result
        
        # Validate output
        output_valid, validation_result = self.validate_output(
            output_text=output_text,
            context=context,
            user_id=user_id,
            threshold=validation_threshold
        )
        
        result['output_valid'] = output_valid
        result['metadata']['validation'] = validation_result
        
        if not output_valid:
            result['error'] = f"Output validation failed: {validation_result.get('issues', [])}"
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get governor statistics."""
        return {
            'rate_limiter': asyncio.run(self.rate_limiter.get_stats()),
            'policy': self.policy_engine.get_policy(),
            'validator_loaded': self.validator.model is not None
        }
    
    def reload_policy(self):
        """Reload policy from file."""
        self.policy_engine.reload_policy()
        logger.info("Policy reloaded in governor")

