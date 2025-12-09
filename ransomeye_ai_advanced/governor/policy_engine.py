# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/governor/policy_engine.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Policy engine that checks inputs/outputs against policy.json for safety

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PolicyEngine:
    """
    Policy engine that enforces safety policies.
    Checks inputs and outputs against policy rules loaded from policy.json.
    """
    
    def __init__(self, policy_path: Optional[str] = None):
        """
        Initialize policy engine.
        
        Args:
            policy_path: Path to policy.json file
        """
        self.policy_path = policy_path or os.environ.get(
            'AI_POLICY_PATH',
            str(Path(__file__).parent.parent / 'config' / 'policy.json')
        )
        self.policy: Dict[str, Any] = {}
        self._load_policy()
    
    def _load_policy(self):
        """Load policy from JSON file."""
        if os.path.exists(self.policy_path):
            try:
                with open(self.policy_path, 'r') as f:
                    self.policy = json.load(f)
                logger.info(f"Loaded policy from {self.policy_path}")
            except Exception as e:
                logger.error(f"Error loading policy: {e}")
                self._create_default_policy()
        else:
            logger.warning(f"Policy file not found at {self.policy_path}, using default")
            self._create_default_policy()
            self._save_policy()
    
    def _create_default_policy(self):
        """Create default policy."""
        self.policy = {
            'blocked_keywords': [
                'password', 'secret', 'api_key', 'token', 'credential',
                'delete all', 'format', 'rm -rf', 'drop table',
                'malware', 'exploit', 'hack', 'crack'
            ],
            'blocked_patterns': [
                r'password\s*[:=]\s*\S+',
                r'api[_-]?key\s*[:=]\s*\S+',
                r'secret\s*[:=]\s*\S+',
                r'rm\s+-rf',
                r'drop\s+table',
                r'delete\s+from\s+\w+'
            ],
            'allowed_domains': [],  # Empty = allow all
            'max_input_length': 10000,
            'max_output_length': 50000,
            'require_verification': True,
            'block_unsafe_commands': True
        }
    
    def _save_policy(self):
        """Save policy to file."""
        try:
            os.makedirs(os.path.dirname(self.policy_path), exist_ok=True)
            with open(self.policy_path, 'w') as f:
                json.dump(self.policy, f, indent=2)
            logger.info(f"Saved default policy to {self.policy_path}")
        except Exception as e:
            logger.error(f"Error saving policy: {e}")
    
    def check_input(self, text: str, user_id: Optional[str] = None) -> Tuple[bool, List[str]]:
        """
        Check input against policy.
        
        Args:
            text: Input text to check
            user_id: Optional user ID
            
        Returns:
            Tuple of (allowed, violations)
        """
        violations = []
        
        # Check length
        max_length = self.policy.get('max_input_length', 10000)
        if len(text) > max_length:
            violations.append(f"Input exceeds maximum length ({max_length} chars)")
            return False, violations
        
        # Check blocked keywords
        text_lower = text.lower()
        blocked_keywords = self.policy.get('blocked_keywords', [])
        for keyword in blocked_keywords:
            if keyword.lower() in text_lower:
                violations.append(f"Contains blocked keyword: {keyword}")
        
        # Check blocked patterns
        blocked_patterns = self.policy.get('blocked_patterns', [])
        for pattern in blocked_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(f"Matches blocked pattern: {pattern}")
        
        # Check for unsafe commands if enabled
        if self.policy.get('block_unsafe_commands', True):
            unsafe_commands = ['rm -rf', 'format', 'del /f', 'drop table', 'delete from']
            for cmd in unsafe_commands:
                if cmd.lower() in text_lower:
                    violations.append(f"Contains unsafe command: {cmd}")
        
        allowed = len(violations) == 0
        return allowed, violations
    
    def check_output(self, text: str, user_id: Optional[str] = None) -> Tuple[bool, List[str]]:
        """
        Check output against policy.
        
        Args:
            text: Output text to check
            user_id: Optional user ID
            
        Returns:
            Tuple of (allowed, violations)
        """
        violations = []
        
        # Check length
        max_length = self.policy.get('max_output_length', 50000)
        if len(text) > max_length:
            violations.append(f"Output exceeds maximum length ({max_length} chars)")
            return False, violations
        
        # Check for sensitive information leakage
        sensitive_patterns = [
            r'password\s*[:=]\s*[^\s]+',
            r'api[_-]?key\s*[:=]\s*[^\s]+',
            r'secret\s*[:=]\s*[^\s]+',
            r'credential\s*[:=]\s*[^\s]+'
        ]
        
        for pattern in sensitive_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(f"Output contains sensitive information pattern: {pattern}")
        
        # Check blocked keywords in output
        text_lower = text.lower()
        blocked_keywords = self.policy.get('blocked_keywords', [])
        for keyword in blocked_keywords:
            # Only check for dangerous keywords in output
            dangerous_keywords = ['password', 'secret', 'api_key', 'token', 'credential']
            if keyword.lower() in dangerous_keywords and keyword.lower() in text_lower:
                # Check if it's just a mention vs actual value
                if re.search(rf'{keyword}\s*[:=]\s*\S+', text, re.IGNORECASE):
                    violations.append(f"Output contains sensitive data: {keyword}")
        
        allowed = len(violations) == 0
        return allowed, violations
    
    def reload_policy(self):
        """Reload policy from file."""
        self._load_policy()
        logger.info("Policy reloaded")
    
    def get_policy(self) -> Dict[str, Any]:
        """Get current policy (read-only)."""
        return self.policy.copy()
    
    def update_policy(self, updates: Dict[str, Any]):
        """
        Update policy (admin function).
        
        Args:
            updates: Dictionary of policy updates
        """
        self.policy.update(updates)
        self._save_policy()
        logger.info("Policy updated")

