# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/security/policy_engine.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Checks inputs against blocked topics using regex/keyword blocklist

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PolicyViolation:
    """Represents a policy violation."""
    violation_type: str
    matched_pattern: str
    severity: str  # 'block', 'warn'
    context: str


class PolicyEngine:
    """
    Policy engine that checks inputs against blocked topics and patterns.
    """
    
    def __init__(self, policy_file: str = None):
        """
        Initialize policy engine.
        
        Args:
            policy_file: Path to blocked_topics.json file
        """
        if policy_file is None:
            policy_file = os.environ.get(
                'BLOCKED_TOPICS_FILE',
                '/home/ransomeye/rebuild/ransomeye_llm_behavior/config/blocked_topics.json'
            )
        
        self.policy_file = Path(policy_file)
        self.blocked_keywords = []
        self.blocked_patterns = []
        self.blocked_regexes = []
        
        self._load_policy()
    
    def _load_policy(self):
        """Load policy from JSON file."""
        if self.policy_file.exists():
            try:
                with open(self.policy_file, 'r') as f:
                    policy = json.load(f)
                
                self.blocked_keywords = policy.get('keywords', [])
                self.blocked_patterns = policy.get('patterns', [])
                
                # Compile regex patterns
                for pattern in self.blocked_patterns:
                    try:
                        self.blocked_regexes.append(re.compile(pattern, re.IGNORECASE))
                    except re.error as e:
                        logger.warning(f"Invalid regex pattern: {pattern} - {e}")
                
                logger.info(f"Loaded policy: {len(self.blocked_keywords)} keywords, {len(self.blocked_regexes)} regexes")
            
            except Exception as e:
                logger.error(f"Error loading policy file: {e}")
                self._load_default_policy()
        else:
            logger.warning(f"Policy file not found: {self.policy_file}")
            self._load_default_policy()
            # Create default policy file
            self._save_default_policy()
    
    def _load_default_policy(self):
        """Load default policy."""
        # Default blocked keywords
        self.blocked_keywords = [
            'password', 'secret', 'api_key', 'token', 'credential',
            'ssn', 'social security', 'credit card', 'bank account'
        ]
        
        # Default regex patterns
        default_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN pattern
            r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Credit card
            r'[A-Za-z0-9+/]{40,}={0,2}',  # Base64 encoded (likely secrets)
        ]
        
        for pattern in default_patterns:
            try:
                self.blocked_regexes.append(re.compile(pattern, re.IGNORECASE))
            except:
                pass
    
    def _save_default_policy(self):
        """Save default policy to file."""
        try:
            self.policy_file.parent.mkdir(parents=True, exist_ok=True)
            policy = {
                'keywords': self.blocked_keywords,
                'patterns': [p.pattern for p in self.blocked_regexes],
                'version': '1.0'
            }
            with open(self.policy_file, 'w') as f:
                json.dump(policy, f, indent=2)
            logger.info(f"Saved default policy to {self.policy_file}")
        except Exception as e:
            logger.error(f"Error saving default policy: {e}")
    
    def check_input(self, text: str) -> Tuple[bool, List[PolicyViolation]]:
        """
        Check input text against policy.
        
        Args:
            text: Input text to check
            
        Returns:
            Tuple of (is_allowed, violations)
        """
        violations = []
        text_lower = text.lower()
        
        # Check keywords
        for keyword in self.blocked_keywords:
            if keyword.lower() in text_lower:
                violations.append(PolicyViolation(
                    violation_type='keyword',
                    matched_pattern=keyword,
                    severity='block',
                    context=self._extract_context(text, keyword)
                ))
        
        # Check regex patterns
        for regex in self.blocked_regexes:
            matches = regex.findall(text)
            if matches:
                violations.append(PolicyViolation(
                    violation_type='regex',
                    matched_pattern=regex.pattern,
                    severity='block',
                    context=f"Matched: {matches[0][:50]}"
                ))
        
        is_allowed = len(violations) == 0
        
        if violations:
            logger.warning(f"Policy violations detected: {len(violations)}")
        
        return is_allowed, violations
    
    def _extract_context(self, text: str, keyword: str, context_length: int = 50) -> str:
        """Extract context around keyword match."""
        idx = text.lower().find(keyword.lower())
        if idx == -1:
            return ""
        
        start = max(0, idx - context_length)
        end = min(len(text), idx + len(keyword) + context_length)
        return text[start:end]

