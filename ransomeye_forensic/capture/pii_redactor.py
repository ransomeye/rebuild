# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/capture/pii_redactor.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Regex-based PII redactor for text streams (SSN, Credit Cards)

import re
from typing import Iterator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PIIRedactor:
    """Regex-based PII redactor for text streams."""
    
    def __init__(self):
        """Initialize PII redactor with regex patterns."""
        # SSN pattern: XXX-XX-XXXX
        self.ssn_pattern = re.compile(
            r'\b\d{3}-\d{2}-\d{4}\b'
        )
        
        # Credit card patterns (various formats)
        self.cc_patterns = [
            # 16 digits with optional dashes/spaces
            re.compile(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'),
            # 13-19 digits (generic)
            re.compile(r'\b\d{13,19}\b')
        ]
        
        # Email pattern
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
        
        # Phone number patterns
        self.phone_patterns = [
            # US format: (XXX) XXX-XXXX
            re.compile(r'\b\(\d{3}\)\s?\d{3}-\d{4}\b'),
            # US format: XXX-XXX-XXXX
            re.compile(r'\b\d{3}-\d{3}-\d{4}\b'),
            # International: +X-XXX-XXX-XXXX
            re.compile(r'\b\+\d{1,3}-\d{3}-\d{3}-\d{4}\b')
        ]
    
    def redact_ssn(self, text: str) -> str:
        """
        Redact SSN patterns.
        
        Args:
            text: Input text
            
        Returns:
            Text with SSNs redacted
        """
        return self.ssn_pattern.sub('[SSN_REDACTED]', text)
    
    def redact_credit_card(self, text: str) -> str:
        """
        Redact credit card patterns.
        
        Args:
            text: Input text
            
        Returns:
            Text with credit cards redacted
        """
        result = text
        for pattern in self.cc_patterns:
            result = pattern.sub('[CC_REDACTED]', result)
        return result
    
    def redact_email(self, text: str) -> str:
        """
        Redact email addresses.
        
        Args:
            text: Input text
            
        Returns:
            Text with emails redacted
        """
        return self.email_pattern.sub('[EMAIL_REDACTED]', text)
    
    def redact_phone(self, text: str) -> str:
        """
        Redact phone numbers.
        
        Args:
            text: Input text
            
        Returns:
            Text with phone numbers redacted
        """
        result = text
        for pattern in self.phone_patterns:
            result = pattern.sub('[PHONE_REDACTED]', result)
        return result
    
    def redact_all(self, text: str) -> str:
        """
        Redact all PII patterns.
        
        Args:
            text: Input text
            
        Returns:
            Text with all PII redacted
        """
        result = text
        result = self.redact_ssn(result)
        result = self.redact_credit_card(result)
        result = self.redact_email(result)
        result = self.redact_phone(result)
        return result
    
    def redact_stream(self, text_stream: Iterator[str]) -> Iterator[str]:
        """
        Redact PII from a text stream.
        
        Args:
            text_stream: Iterator yielding text strings
            
        Yields:
            Redacted text strings
        """
        for text in text_stream:
            yield self.redact_all(text)
    
    def redact_file(self, input_path: str, output_path: str, chunk_size: int = 8192):
        """
        Redact PII from a file.
        
        Args:
            input_path: Path to input file
            output_path: Path to output file
            chunk_size: Size of chunks to read
        """
        with open(input_path, 'r', encoding='utf-8', errors='ignore') as infile:
            with open(output_path, 'w', encoding='utf-8') as outfile:
                buffer = ''
                
                while True:
                    chunk = infile.read(chunk_size)
                    if not chunk:
                        break
                    
                    buffer += chunk
                    
                    # Process complete lines
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        redacted = self.redact_all(line)
                        outfile.write(redacted + '\n')
                
                # Process remaining buffer
                if buffer:
                    redacted = self.redact_all(buffer)
                    outfile.write(redacted)
        
        logger.info(f"Redacted PII: {input_path} -> {output_path}")

