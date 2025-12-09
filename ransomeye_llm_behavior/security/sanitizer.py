# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/security/sanitizer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Redacts PII (IPs, Keys, SSNs) from LLM output before it leaves the system

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Redaction:
    """Represents a PII redaction."""
    redaction_type: str
    original: str
    redacted: str
    position: int


class PIISanitizer:
    """
    Sanitizes LLM output by redacting PII before it leaves the system.
    """
    
    def __init__(self):
        """Initialize PII sanitizer with detection patterns."""
        # IP address patterns
        self.ipv4_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        self.ipv6_pattern = re.compile(r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b')
        
        # SSN pattern
        self.ssn_pattern = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
        
        # API keys / tokens (common patterns)
        self.api_key_patterns = [
            re.compile(r'\b[A-Za-z0-9]{32,}\b'),  # Long alphanumeric strings
            re.compile(r'sk-[A-Za-z0-9]{20,}'),  # Stripe-like keys
            re.compile(r'AKIA[0-9A-Z]{16}'),  # AWS access keys
            re.compile(r'ghp_[A-Za-z0-9]{36}'),  # GitHub tokens
        ]
        
        # Email addresses
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        
        # Credit card numbers
        self.credit_card_pattern = re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b')
        
        # MAC addresses
        self.mac_pattern = re.compile(r'\b(?:[0-9A-Fa-f]{2}[:-]){5}(?:[0-9A-Fa-f]{2})\b')
    
    def sanitize(self, text: str, redact_types: List[str] = None) -> Tuple[str, List[Redaction]]:
        """
        Sanitize text by redacting PII.
        
        Args:
            text: Text to sanitize
            redact_types: List of types to redact (None = all)
            
        Returns:
            Tuple of (sanitized_text, redactions)
        """
        if redact_types is None:
            redact_types = ['ip', 'ssn', 'api_key', 'email', 'credit_card', 'mac']
        
        redactions = []
        sanitized = text
        
        # Redact in reverse order to preserve positions
        redaction_functions = {
            'ip': self._redact_ips,
            'ssn': self._redact_ssns,
            'api_key': self._redact_api_keys,
            'email': self._redact_emails,
            'credit_card': self._redact_credit_cards,
            'mac': self._redact_macs,
        }
        
        for redact_type in redact_types:
            if redact_type in redaction_functions:
                sanitized, new_redactions = redaction_functions[redact_type](sanitized)
                redactions.extend(new_redactions)
        
        if redactions:
            logger.info(f"Redacted {len(redactions)} PII items")
        
        return sanitized, redactions
    
    def _redact_ips(self, text: str) -> Tuple[str, List[Redaction]]:
        """Redact IP addresses."""
        redactions = []
        
        # IPv4
        for match in self.ipv4_pattern.finditer(text):
            # Validate IP (basic check)
            parts = match.group().split('.')
            if all(0 <= int(p) <= 255 for p in parts):
                redactions.append(Redaction(
                    redaction_type='ipv4',
                    original=match.group(),
                    redacted='[IP_REDACTED]',
                    position=match.start()
                ))
        
        # IPv6
        for match in self.ipv6_pattern.finditer(text):
            redactions.append(Redaction(
                redaction_type='ipv6',
                original=match.group(),
                redacted='[IP_REDACTED]',
                position=match.start()
            ))
        
        # Apply redactions (in reverse order)
        for redaction in sorted(redactions, key=lambda x: x.position, reverse=True):
            text = text[:redaction.position] + redaction.redacted + text[redaction.position + len(redaction.original):]
        
        return text, redactions
    
    def _redact_ssns(self, text: str) -> Tuple[str, List[Redaction]]:
        """Redact SSNs."""
        redactions = []
        
        for match in self.ssn_pattern.finditer(text):
            redactions.append(Redaction(
                redaction_type='ssn',
                original=match.group(),
                redacted='[SSN_REDACTED]',
                position=match.start()
            ))
        
        for redaction in sorted(redactions, key=lambda x: x.position, reverse=True):
            text = text[:redaction.position] + redaction.redacted + text[redaction.position + len(redaction.original):]
        
        return text, redactions
    
    def _redact_api_keys(self, text: str) -> Tuple[str, List[Redaction]]:
        """Redact API keys and tokens."""
        redactions = []
        
        for pattern in self.api_key_patterns:
            for match in pattern.finditer(text):
                # Skip if it's part of a URL or email
                start, end = match.span()
                if start > 0 and text[start-1] in ['@', '/', '=']:
                    continue
                
                redactions.append(Redaction(
                    redaction_type='api_key',
                    original=match.group(),
                    redacted='[API_KEY_REDACTED]',
                    position=match.start()
                ))
        
        for redaction in sorted(redactions, key=lambda x: x.position, reverse=True):
            text = text[:redaction.position] + redaction.redacted + text[redaction.position + len(redaction.original):]
        
        return text, redactions
    
    def _redact_emails(self, text: str) -> Tuple[str, List[Redaction]]:
        """Redact email addresses."""
        redactions = []
        
        for match in self.email_pattern.finditer(text):
            redactions.append(Redaction(
                redaction_type='email',
                original=match.group(),
                redacted='[EMAIL_REDACTED]',
                position=match.start()
            ))
        
        for redaction in sorted(redactions, key=lambda x: x.position, reverse=True):
            text = text[:redaction.position] + redaction.redacted + text[redaction.position + len(redaction.original):]
        
        return text, redactions
    
    def _redact_credit_cards(self, text: str) -> Tuple[str, List[Redaction]]:
        """Redact credit card numbers."""
        redactions = []
        
        for match in self.credit_card_pattern.finditer(text):
            redactions.append(Redaction(
                redaction_type='credit_card',
                original=match.group(),
                redacted='[CARD_REDACTED]',
                position=match.start()
            ))
        
        for redaction in sorted(redactions, key=lambda x: x.position, reverse=True):
            text = text[:redaction.position] + redaction.redacted + text[redaction.position + len(redaction.original):]
        
        return text, redactions
    
    def _redact_macs(self, text: str) -> Tuple[str, List[Redaction]]:
        """Redact MAC addresses."""
        redactions = []
        
        for match in self.mac_pattern.finditer(text):
            redactions.append(Redaction(
                redaction_type='mac',
                original=match.group(),
                redacted='[MAC_REDACTED]',
                position=match.start()
            ))
        
        for redaction in sorted(redactions, key=lambda x: x.position, reverse=True):
            text = text[:redaction.position] + redaction.redacted + text[redaction.position + len(redaction.original):]
        
        return text, redactions

