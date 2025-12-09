# Path and File Name : /home/ransomeye/rebuild/ransomeye_dpi_probe/engine/privacy_filter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: PII redaction filter using regex patterns for credit cards, SSNs, and other sensitive data

import os
import re
import logging
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


class PrivacyFilter:
    """Redacts PII from packet payloads based on configurable rules."""
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize privacy filter.
        
        Args:
            strict_mode: If True, apply all redaction rules (default: True)
        """
        self.strict_mode = strict_mode
        self.redact_enabled = os.environ.get('PROBE_PRIVACY_REDACT', 'strict').lower() in ['true', 'strict', '1', 'yes']
        
        # Credit card patterns (Luhn-validated ranges)
        self.cc_patterns = [
            re.compile(r'\b(?:4[0-9]{12}(?:[0-9]{3})?)\b'),  # Visa
            re.compile(r'\b(?:5[1-5][0-9]{14})\b'),  # MasterCard
            re.compile(r'\b(?:3[47][0-9]{13})\b'),  # Amex
            re.compile(r'\b(?:3[0-9]{13})\b'),  # Diners Club
            re.compile(r'\b(?:6(?:011|5[0-9]{2})[0-9]{12})\b'),  # Discover
        ]
        
        # SSN pattern (XXX-XX-XXXX)
        self.ssn_pattern = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
        
        # Email addresses
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        
        # IP addresses (private/internal)
        self.private_ip_pattern = re.compile(
            r'\b(?:10\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|'
            r'172\.(?:1[6-9]|2[0-9]|3[01])\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|'
            r'192\.168\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))\b'
        )
        
        # API keys/tokens (heuristically)
        self.api_key_pattern = re.compile(r'\b(?:api[_-]?key|token|secret)[=:]\s*([A-Za-z0-9_-]{20,})\b', re.IGNORECASE)
        
        # Passwords (heuristically)
        self.password_pattern = re.compile(r'\b(?:password|pwd|passwd)[=:]\s*([^\s&"\'<>]{8,})\b', re.IGNORECASE)
        
        self.redacted_bytes = 0
        self.redaction_stats = {
            'credit_cards': 0,
            'ssns': 0,
            'emails': 0,
            'private_ips': 0,
            'api_keys': 0,
            'passwords': 0,
        }
    
    def redact(self, payload: bytes, flow_id: str = None) -> Tuple[bytes, Dict[str, Any]]:
        """
        Redact PII from payload bytes.
        
        Args:
            payload: Raw packet payload
            flow_id: Optional flow identifier for logging
            
        Returns:
            Tuple of (redacted_payload, redaction_stats)
        """
        if not self.redact_enabled or not payload:
            return payload, {'redacted': False, 'stats': {}}
        
        original_len = len(payload)
        redacted = payload.decode('utf-8', errors='ignore')
        
        stats = {
            'redacted': False,
            'patterns_matched': [],
            'bytes_removed': 0
        }
        
        # Redact credit cards
        for pattern in self.cc_patterns:
            matches = pattern.findall(redacted)
            if matches:
                stats['redacted'] = True
                stats['patterns_matched'].append('credit_card')
                self.redaction_stats['credit_cards'] += len(matches)
                for match in matches:
                    # Replace with masked version (last 4 digits visible)
                    if len(match) >= 4:
                        masked = 'XXXX-XXXX-XXXX-' + match[-4:]
                        redacted = redacted.replace(match, masked)
        
        # Redact SSNs
        ssn_matches = self.ssn_pattern.findall(redacted)
        if ssn_matches:
            stats['redacted'] = True
            stats['patterns_matched'].append('ssn')
            self.redaction_stats['ssns'] += len(ssn_matches)
            for match in ssn_matches:
                masked = 'XXX-XX-' + match[-4:]
                redacted = redacted.replace(match, masked)
        
        # Redact emails (optional in strict mode)
        if self.strict_mode:
            email_matches = self.email_pattern.findall(redacted)
            if email_matches:
                stats['redacted'] = True
                stats['patterns_matched'].append('email')
                self.redaction_stats['emails'] += len(email_matches)
                for match in email_matches:
                    parts = match.split('@')
                    if len(parts) == 2:
                        masked = parts[0][0] + '***@' + parts[1]
                        redacted = redacted.replace(match, masked)
        
        # Redact private IPs
        ip_matches = self.private_ip_pattern.findall(redacted)
        if ip_matches:
            stats['redacted'] = True
            stats['patterns_matched'].append('private_ip')
            self.redaction_stats['private_ips'] += len(ip_matches)
            for match in ip_matches:
                masked = match.rsplit('.', 1)[0] + '.XXX'
                redacted = redacted.replace(match, masked)
        
        # Redact API keys
        api_matches = self.api_key_pattern.findall(redacted)
        if api_matches:
            stats['redacted'] = True
            stats['patterns_matched'].append('api_key')
            self.redaction_stats['api_keys'] += len(api_matches)
            for match in api_matches:
                masked = match[:4] + '***' + match[-4:] if len(match) > 8 else '***'
                redacted = redacted.replace(match, masked)
        
        # Redact passwords
        pwd_matches = self.password_pattern.findall(redacted)
        if pwd_matches:
            stats['redacted'] = True
            stats['patterns_matched'].append('password')
            self.redaction_stats['passwords'] += len(pwd_matches)
            for match in pwd_matches:
                redacted = redacted.replace(match, '***REDACTED***')
        
        redacted_bytes_result = bytes(redacted, 'utf-8', errors='ignore')
        stats['bytes_removed'] = original_len - len(redacted_bytes_result)
        self.redacted_bytes += stats['bytes_removed']
        
        if stats['redacted'] and flow_id:
            logger.debug(f"Redacted PII in flow {flow_id}: {stats['patterns_matched']}")
        
        return redacted_bytes_result, stats
    
    def get_stats(self) -> Dict[str, Any]:
        """Get redaction statistics."""
        return {
            'total_redacted_bytes': self.redacted_bytes,
            'pattern_counts': self.redaction_stats.copy(),
            'enabled': self.redact_enabled,
            'strict_mode': self.strict_mode
        }
    
    def reset_stats(self):
        """Reset statistics counters."""
        self.redacted_bytes = 0
        self.redaction_stats = {
            'credit_cards': 0,
            'ssns': 0,
            'emails': 0,
            'private_ips': 0,
            'api_keys': 0,
            'passwords': 0,
        }

