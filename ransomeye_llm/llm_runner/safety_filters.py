# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm/llm_runner/safety_filters.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Regex-based output sanitizer for PII redaction

import os
import re
import logging
from typing import str as String

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SafetyFilters:
    """
    Safety filters for sanitizing LLM output.
    Redacts PII if enabled.
    """
    
    def __init__(self):
        """Initialize safety filters."""
        self.pii_redact_enabled = os.environ.get('PII_REDACT_ENABLED', 'false').lower() == 'true'
        
        # IP address pattern
        self.ip_pattern = re.compile(
            r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
        )
        
        # Email pattern
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
        
        # SSN pattern
        self.ssn_pattern = re.compile(
            r'\b\d{3}-\d{2}-\d{4}\b'
        )
        
        # Credit card pattern
        self.cc_pattern = re.compile(
            r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'
        )
        
        # MAC address pattern
        self.mac_pattern = re.compile(
            r'\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b'
        )
    
    def sanitize(self, text: str) -> str:
        """
        Sanitize text by redacting PII if enabled.
        
        Args:
            text: Input text
            
        Returns:
            Sanitized text
        """
        if not self.pii_redact_enabled:
            return text
        
        result = text
        
        # Redact IP addresses
        result = self.ip_pattern.sub('[IP_REDACTED]', result)
        
        # Redact email addresses
        result = self.email_pattern.sub('[EMAIL_REDACTED]', result)
        
        # Redact SSNs
        result = self.ssn_pattern.sub('[SSN_REDACTED]', result)
        
        # Redact credit cards
        result = self.cc_pattern.sub('[CC_REDACTED]', result)
        
        # Redact MAC addresses
        result = self.mac_pattern.sub('[MAC_REDACTED]', result)
        
        return result
    
    def redact_ips(self, text: str) -> str:
        """
        Redact IP addresses.
        
        Args:
            text: Input text
            
        Returns:
            Text with IPs redacted
        """
        return self.ip_pattern.sub('[IP_REDACTED]', text)
    
    def redact_emails(self, text: str) -> str:
        """
        Redact email addresses.
        
        Args:
            text: Input text
            
        Returns:
            Text with emails redacted
        """
        return self.email_pattern.sub('[EMAIL_REDACTED]', text)
    
    def filter_sensitive_content(self, text: str) -> str:
        """
        Filter sensitive content from text.
        
        Args:
            text: Input text
            
        Returns:
            Filtered text
        """
        # Remove potential command injection patterns
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
        ]
        
        result = text
        for pattern in dangerous_patterns:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE | re.DOTALL)
        
        return result
    
    def sanitize_output(self, text: str) -> str:
        """
        Full sanitization pipeline.
        
        Args:
            text: Input text
            
        Returns:
            Fully sanitized text
        """
        # First filter dangerous content
        result = self.filter_sensitive_content(text)
        
        # Then redact PII if enabled
        result = self.sanitize(result)
        
        return result

