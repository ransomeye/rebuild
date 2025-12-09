# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/normalizer/normalizer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Canonicalization logic for IP (IPv6 expand/compress), Domain (lowercase, strip protocols), Hash (lowercase)

import ipaddress
import re
from typing import Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IOCNormalizer:
    """
    Normalizes IOCs to canonical form:
    - IP: Expand/Compress IPv6 to standard form
    - Domain: Lowercase, strip protocols
    - Hash: Lowercase
    """
    
    def normalize(self, ioc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize an IOC to canonical form.
        
        Args:
            ioc: IOC dictionary with 'value' and 'type'
            
        Returns:
            Normalized IOC dictionary
        """
        normalized = ioc.copy()
        value = ioc.get('value', '')
        ioc_type = ioc.get('type', '').lower()
        
        if not value:
            return normalized
        
        # Normalize based on type
        if ioc_type in ['ipv4', 'ip']:
            normalized_value = self._normalize_ipv4(value)
        elif ioc_type in ['ipv6']:
            normalized_value = self._normalize_ipv6(value)
        elif ioc_type in ['domain', 'domain-name', 'fqdn']:
            normalized_value = self._normalize_domain(value)
        elif ioc_type in ['hash', 'md5', 'sha1', 'sha256', 'sha512']:
            normalized_value = self._normalize_hash(value)
        elif ioc_type in ['url', 'uri']:
            normalized_value = self._normalize_url(value)
        else:
            # Try to infer type and normalize
            normalized_value = self._normalize_unknown(value)
            if normalized_value != value:
                # Type was inferred
                normalized['type'] = self._infer_type(normalized_value)
        
        normalized['value'] = normalized_value
        normalized['normalized_at'] = self._get_timestamp()
        
        return normalized
    
    def _normalize_ipv4(self, value: str) -> str:
        """
        Normalize IPv4 address.
        
        Args:
            value: IPv4 address string
            
        Returns:
            Normalized IPv4 address
        """
        try:
            ip = ipaddress.IPv4Address(value.strip())
            return str(ip)
        except ValueError:
            logger.warning(f"Invalid IPv4: {value}")
            return value.strip()
    
    def _normalize_ipv6(self, value: str) -> str:
        """
        Normalize IPv6 address (expand to full form, then compress to standard).
        
        Args:
            value: IPv6 address string
            
        Returns:
            Normalized IPv6 address (compressed standard form)
        """
        try:
            # Remove brackets if present
            value = value.strip().strip('[]')
            
            ip = ipaddress.IPv6Address(value)
            # Return in compressed standard form
            return ip.compressed
        except ValueError:
            logger.warning(f"Invalid IPv6: {value}")
            return value.strip()
    
    def _normalize_domain(self, value: str) -> str:
        """
        Normalize domain name (lowercase, strip protocols).
        
        Args:
            value: Domain string
            
        Returns:
            Normalized domain
        """
        # Remove protocol
        value = re.sub(r'^https?://', '', value, flags=re.IGNORECASE)
        value = re.sub(r'^ftp://', '', value, flags=re.IGNORECASE)
        
        # Remove path
        value = value.split('/')[0]
        
        # Remove port
        value = value.split(':')[0]
        
        # Remove query parameters
        value = value.split('?')[0]
        
        # Lowercase
        value = value.lower().strip()
        
        # Remove trailing dot
        value = value.rstrip('.')
        
        return value
    
    def _normalize_hash(self, value: str) -> str:
        """
        Normalize hash (lowercase).
        
        Args:
            value: Hash string
            
        Returns:
            Normalized hash (lowercase)
        """
        return value.strip().lower()
    
    def _normalize_url(self, value: str) -> str:
        """
        Normalize URL.
        
        Args:
            value: URL string
            
        Returns:
            Normalized URL
        """
        # Lowercase scheme and domain
        value = value.strip()
        
        # Extract components
        match = re.match(r'^([^:]+)://([^/]+)(.*)$', value, re.IGNORECASE)
        if match:
            scheme = match.group(1).lower()
            domain = self._normalize_domain(match.group(2))
            path = match.group(3)
            return f"{scheme}://{domain}{path}"
        
        return value
    
    def _normalize_unknown(self, value: str) -> str:
        """
        Try to normalize unknown type by inferring type.
        
        Args:
            value: Unknown value
            
        Returns:
            Normalized value
        """
        # Try IP
        try:
            ipaddress.ip_address(value)
            return self._normalize_ipv4(value) if '.' in value else self._normalize_ipv6(value)
        except ValueError:
            pass
        
        # Try domain
        if '.' in value and not value.startswith('/'):
            return self._normalize_domain(value)
        
        # Try hash
        if len(value) in [32, 40, 64] and all(c in '0123456789abcdefABCDEF' for c in value):
            return self._normalize_hash(value)
        
        # Try URL
        if value.startswith(('http://', 'https://')):
            return self._normalize_url(value)
        
        return value.strip()
    
    def _infer_type(self, value: str) -> str:
        """
        Infer IOC type from value.
        
        Args:
            value: IOC value
            
        Returns:
            Inferred type
        """
        # Try IP
        try:
            ipaddress.ip_address(value)
            return 'ipv6' if ':' in value else 'ipv4'
        except ValueError:
            pass
        
        # Try domain
        if '.' in value and not value.startswith('/'):
            return 'domain'
        
        # Try hash
        if len(value) in [32, 40, 64] and all(c in '0123456789abcdef' for c in value.lower()):
            return 'hash'
        
        # Try URL
        if value.startswith(('http://', 'https://')):
            return 'url'
        
        return 'unknown'
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat()

