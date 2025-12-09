# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/dedup/fingerprint.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Generates deterministic hashes (sha256(type + value)) for IOC fingerprinting

import hashlib
from typing import Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IOCFingerprint:
    """
    Generates deterministic fingerprints for IOCs.
    Uses SHA256(type + normalized_value) for exact matching.
    """
    
    @staticmethod
    def generate(ioc: Dict[str, Any]) -> str:
        """
        Generate fingerprint for IOC.
        
        Args:
            ioc: IOC dictionary with 'type' and 'value'
            
        Returns:
            SHA256 fingerprint (hex string)
        """
        ioc_type = ioc.get('type', 'unknown')
        value = ioc.get('value', '')
        
        # Normalize for fingerprinting
        normalized_value = value.strip().lower()
        
        # Create fingerprint: sha256(type + value)
        fingerprint_string = f"{ioc_type}:{normalized_value}"
        fingerprint = hashlib.sha256(fingerprint_string.encode('utf-8')).hexdigest()
        
        return fingerprint
    
    @staticmethod
    def generate_from_value(ioc_type: str, value: str) -> str:
        """
        Generate fingerprint from type and value.
        
        Args:
            ioc_type: IOC type
            value: IOC value
            
        Returns:
            SHA256 fingerprint
        """
        return IOCFingerprint.generate({'type': ioc_type, 'value': value})

