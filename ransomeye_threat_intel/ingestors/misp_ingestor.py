# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/ingestors/misp_ingestor.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Adapter for STIX 2.1 JSON (Wiz/MITRE format) ingestion

import os
import json
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Try to import stix2
try:
    import stix2
    STIX2_AVAILABLE = True
except ImportError:
    STIX2_AVAILABLE = False
    logging.warning("stix2 library not available. Install: pip install stix2")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MISPIngestor:
    """
    Ingestor for STIX 2.1 JSON feeds (Wiz/MITRE format).
    Parses STIX Indicator and Malware objects.
    """
    
    def __init__(
        self,
        misp_url: Optional[str] = None,
        misp_key: Optional[str] = None
    ):
        """
        Initialize MISP ingestor.
        
        Args:
            misp_url: MISP instance URL
            misp_key: MISP API key
        """
        self.misp_url = misp_url or os.environ.get('MISP_URL', '')
        self.misp_key = misp_key or os.environ.get('MISP_KEY', '')
        self.headers = {
            'Authorization': self.misp_key,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def ingest_stix_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Ingest STIX 2.1 JSON from file.
        
        Args:
            file_path: Path to STIX JSON file
            
        Returns:
            List of parsed IOC dictionaries
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            return self._parse_stix_bundle(data)
        except Exception as e:
            logger.error(f"Error ingesting STIX file {file_path}: {e}")
            return []
    
    def ingest_stix_string(self, stix_json: str) -> List[Dict[str, Any]]:
        """
        Ingest STIX 2.1 JSON from string.
        
        Args:
            stix_json: STIX JSON string
            
        Returns:
            List of parsed IOC dictionaries
        """
        try:
            data = json.loads(stix_json)
            return self._parse_stix_bundle(data)
        except Exception as e:
            logger.error(f"Error parsing STIX JSON: {e}")
            return []
    
    def fetch_from_misp(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Fetch IOCs from MISP API.
        
        Args:
            filters: Optional MISP search filters
            
        Returns:
            List of parsed IOC dictionaries
        """
        if not self.misp_url or not self.misp_key:
            logger.warning("MISP URL or key not configured")
            return []
        
        try:
            # MISP API endpoint for STIX export
            url = f"{self.misp_url}/attributes/restSearch"
            params = filters or {}
            
            response = requests.post(
                url,
                headers=self.headers,
                json=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            return self._parse_misp_response(data)
        except Exception as e:
            logger.error(f"Error fetching from MISP: {e}")
            return []
    
    def _parse_stix_bundle(self, bundle_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse STIX 2.1 bundle.
        
        Args:
            bundle_data: STIX bundle dictionary
            
        Returns:
            List of IOC dictionaries
        """
        iocs = []
        
        # Handle STIX 2.1 bundle format
        objects = bundle_data.get('objects', [])
        
        for obj in objects:
            obj_type = obj.get('type', '')
            
            if obj_type == 'indicator':
                ioc = self._parse_indicator(obj)
                if ioc:
                    iocs.append(ioc)
            elif obj_type == 'malware':
                # Extract IOCs from malware object
                malware_iocs = self._parse_malware(obj)
                iocs.extend(malware_iocs)
            elif obj_type == 'observable':
                ioc = self._parse_observable(obj)
                if ioc:
                    iocs.append(ioc)
        
        logger.info(f"Parsed {len(iocs)} IOCs from STIX bundle")
        return iocs
    
    def _parse_indicator(self, indicator: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse STIX Indicator object.
        
        Args:
            indicator: STIX Indicator object
            
        Returns:
            IOC dictionary or None
        """
        try:
            pattern = indicator.get('pattern', '')
            value = self._extract_value_from_pattern(pattern)
            
            if not value:
                return None
            
            ioc_type = self._determine_ioc_type(value, pattern)
            
            return {
                'value': value,
                'type': ioc_type,
                'source': 'stix_indicator',
                'source_id': indicator.get('id', ''),
                'first_seen': indicator.get('created', ''),
                'last_seen': indicator.get('modified', ''),
                'description': indicator.get('description', ''),
                'labels': indicator.get('labels', []),
                'tags': indicator.get('labels', []),
                'confidence': indicator.get('confidence', 50),
                'raw': indicator
            }
        except Exception as e:
            logger.error(f"Error parsing indicator: {e}")
            return None
    
    def _parse_malware(self, malware: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse STIX Malware object.
        
        Args:
            malware: STIX Malware object
            
        Returns:
            List of IOC dictionaries
        """
        iocs = []
        
        # Extract IOCs from malware relationships
        # This is a simplified parser - real implementation would traverse relationships
        malware_id = malware.get('id', '')
        name = malware.get('name', '')
        
        # Create a tag-based IOC
        iocs.append({
            'value': name,
            'type': 'malware_family',
            'source': 'stix_malware',
            'source_id': malware_id,
            'first_seen': malware.get('created', ''),
            'description': malware.get('description', ''),
            'tags': malware.get('labels', []),
            'raw': malware
        })
        
        return iocs
    
    def _parse_observable(self, observable: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse STIX Observable object.
        
        Args:
            observable: STIX Observable object
            
        Returns:
            IOC dictionary or None
        """
        try:
            # Extract value from observable
            objects = observable.get('objects', [])
            if not objects:
                return None
            
            obj = objects[0]
            value = obj.get('value', '')
            
            if not value:
                return None
            
            ioc_type = self._determine_ioc_type(value)
            
            return {
                'value': value,
                'type': ioc_type,
                'source': 'stix_observable',
                'source_id': observable.get('id', ''),
                'first_seen': observable.get('created', ''),
                'raw': observable
            }
        except Exception as e:
            logger.error(f"Error parsing observable: {e}")
            return None
    
    def _extract_value_from_pattern(self, pattern: str) -> Optional[str]:
        """
        Extract IOC value from STIX pattern.
        
        Args:
            pattern: STIX pattern string (e.g., "[ipv4-addr:value = '192.168.1.1']")
            
        Returns:
            Extracted value or None
        """
        if not pattern:
            return None
        
        # Simple pattern extraction
        # Real implementation would use STIX pattern parser
        import re
        
        # Match patterns like: [ipv4-addr:value = '192.168.1.1']
        match = re.search(r"=\s*['\"]([^'\"]+)['\"]", pattern)
        if match:
            return match.group(1)
        
        return None
    
    def _determine_ioc_type(self, value: str, pattern: str = '') -> str:
        """
        Determine IOC type from value and pattern.
        
        Args:
            value: IOC value
            pattern: Optional STIX pattern
            
        Returns:
            IOC type (ipv4, ipv6, domain, hash, url, etc.)
        """
        # Check pattern first
        if 'ipv4-addr' in pattern.lower():
            return 'ipv4'
        elif 'ipv6-addr' in pattern.lower():
            return 'ipv6'
        elif 'domain-name' in pattern.lower():
            return 'domain'
        elif 'url' in pattern.lower():
            return 'url'
        elif 'file:hashes' in pattern.lower():
            return 'hash'
        
        # Fallback: infer from value
        import ipaddress
        
        # Check IP
        try:
            ipaddress.ip_address(value)
            if ':' in value:
                return 'ipv6'
            return 'ipv4'
        except ValueError:
            pass
        
        # Check domain
        if '.' in value and not value.startswith('http'):
            # Simple domain check
            if not value.startswith('/') and ' ' not in value:
                return 'domain'
        
        # Check hash
        if len(value) in [32, 40, 64] and all(c in '0123456789abcdefABCDEF' for c in value):
            return 'hash'
        
        # Check URL
        if value.startswith(('http://', 'https://')):
            return 'url'
        
        return 'unknown'
    
    def _parse_misp_response(self, misp_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse MISP API response.
        
        Args:
            misp_data: MISP API response
            
        Returns:
            List of IOC dictionaries
        """
        iocs = []
        attributes = misp_data.get('Attribute', [])
        
        for attr in attributes:
            ioc = {
                'value': attr.get('value', ''),
                'type': attr.get('type', '').lower(),
                'source': 'misp',
                'source_id': str(attr.get('id', '')),
                'first_seen': attr.get('first_seen', ''),
                'last_seen': attr.get('timestamp', ''),
                'description': attr.get('comment', ''),
                'tags': [tag.get('name', '') for tag in attr.get('Tag', [])],
                'confidence': 50,  # Default
                'raw': attr
            }
            iocs.append(ioc)
        
        return iocs

