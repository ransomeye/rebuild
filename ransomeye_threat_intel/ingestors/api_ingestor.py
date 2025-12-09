# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/ingestors/api_ingestor.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Generic HTTP ingestor for JSON/CSV endpoints (Ransomware.live/MalwareBazaar)

import os
import csv
import json
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APIIngestor:
    """
    Generic HTTP ingestor for JSON/CSV endpoints.
    Supports Ransomware.live, MalwareBazaar, and other API-based feeds.
    """
    
    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize API ingestor.
        
        Args:
            api_url: API endpoint URL
            api_key: Optional API key
            headers: Optional custom headers
        """
        self.api_url = api_url
        self.api_key = api_key
        self.headers = headers or {}
        if self.api_key:
            self.headers['Authorization'] = f'Bearer {self.api_key}'
    
    def ingest_json(self, url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Ingest JSON from URL.
        
        Args:
            url: Optional URL (uses self.api_url if not provided)
            
        Returns:
            List of IOC dictionaries
        """
        url = url or self.api_url
        if not url:
            logger.error("No URL provided")
            return []
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            return self._parse_json_response(data, url)
        except Exception as e:
            logger.error(f"Error ingesting JSON from {url}: {e}")
            return []
    
    def ingest_csv(self, url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Ingest CSV from URL.
        
        Args:
            url: Optional URL (uses self.api_url if not provided)
            
        Returns:
            List of IOC dictionaries
        """
        url = url or self.api_url
        if not url:
            logger.error("No URL provided")
            return []
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # Decode response
            content = response.content.decode('utf-8')
            csv_reader = csv.DictReader(content.splitlines())
            
            iocs = []
            for row in csv_reader:
                ioc = self._parse_csv_row(row, url)
                if ioc:
                    iocs.append(ioc)
            
            return iocs
        except Exception as e:
            logger.error(f"Error ingesting CSV from {url}: {e}")
            return []
    
    def ingest_malwarebazaar(self) -> List[Dict[str, Any]]:
        """
        Ingest from MalwareBazaar API.
        
        Returns:
            List of IOC dictionaries
        """
        # MalwareBazaar API endpoint
        url = "https://mb-api.abuse.ch/api/v1/"
        
        # Get recent samples
        data = {
            'query': 'get_recent',
            'selector': '100'
        }
        
        try:
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            iocs = []
            if result.get('query_status') == 'ok':
                samples = result.get('data', [])
                for sample in samples:
                    ioc = {
                        'value': sample.get('sha256_hash', ''),
                        'type': 'hash',
                        'hash_type': 'sha256',
                        'source': 'malwarebazaar',
                        'source_id': sample.get('sha256_hash', ''),
                        'first_seen': sample.get('first_seen', ''),
                        'last_seen': sample.get('last_seen', ''),
                        'description': f"Malware: {sample.get('malware', 'unknown')}",
                        'tags': [sample.get('malware', '')],
                        'confidence': 80,
                        'raw': sample
                    }
                    iocs.append(ioc)
            
            logger.info(f"Ingested {len(iocs)} IOCs from MalwareBazaar")
            return iocs
        except Exception as e:
            logger.error(f"Error ingesting from MalwareBazaar: {e}")
            return []
    
    def ingest_ransomware_live(self) -> List[Dict[str, Any]]:
        """
        Ingest from Ransomware.live API.
        
        Returns:
            List of IOC dictionaries
        """
        url = "https://ransomware.live/api/v1/ransomware"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            iocs = []
            if isinstance(data, list):
                for entry in data:
                    # Extract IOCs from ransomware entry
                    ioc = {
                        'value': entry.get('name', ''),
                        'type': 'ransomware_family',
                        'source': 'ransomware_live',
                        'source_id': str(entry.get('id', '')),
                        'first_seen': entry.get('first_seen', ''),
                        'last_seen': entry.get('last_seen', ''),
                        'description': entry.get('description', ''),
                        'tags': [entry.get('group', '')],
                        'confidence': 70,
                        'raw': entry
                    }
                    iocs.append(ioc)
            
            logger.info(f"Ingested {len(iocs)} IOCs from Ransomware.live")
            return iocs
        except Exception as e:
            logger.error(f"Error ingesting from Ransomware.live: {e}")
            return []
    
    def _parse_json_response(self, data: Any, source_url: str) -> List[Dict[str, Any]]:
        """
        Parse JSON response into IOCs.
        
        Args:
            data: JSON data
            source_url: Source URL for provenance
            
        Returns:
            List of IOC dictionaries
        """
        iocs = []
        
        # Handle different JSON structures
        if isinstance(data, list):
            for item in data:
                ioc = self._extract_ioc_from_dict(item, source_url)
                if ioc:
                    iocs.append(ioc)
        elif isinstance(data, dict):
            # Check for common structures
            if 'data' in data:
                items = data['data']
                if isinstance(items, list):
                    for item in items:
                        ioc = self._extract_ioc_from_dict(item, source_url)
                        if ioc:
                            iocs.append(ioc)
            else:
                ioc = self._extract_ioc_from_dict(data, source_url)
                if ioc:
                    iocs.append(ioc)
        
        return iocs
    
    def _extract_ioc_from_dict(self, item: Dict[str, Any], source_url: str) -> Optional[Dict[str, Any]]:
        """
        Extract IOC from dictionary.
        
        Args:
            item: Dictionary item
            source_url: Source URL
            
        Returns:
            IOC dictionary or None
        """
        # Try common field names
        value = item.get('value') or item.get('ioc') or item.get('indicator') or item.get('hash')
        if not value:
            return None
        
        ioc_type = item.get('type') or item.get('ioc_type') or 'unknown'
        
        return {
            'value': str(value),
            'type': str(ioc_type).lower(),
            'source': 'api',
            'source_id': str(item.get('id', '')),
            'source_url': source_url,
            'first_seen': item.get('first_seen', '') or item.get('created', ''),
            'last_seen': item.get('last_seen', '') or item.get('updated', ''),
            'description': item.get('description', '') or item.get('comment', ''),
            'tags': item.get('tags', []) or item.get('labels', []),
            'confidence': item.get('confidence', 50),
            'raw': item
        }
    
    def _parse_csv_row(self, row: Dict[str, str], source_url: str) -> Optional[Dict[str, Any]]:
        """
        Parse CSV row into IOC.
        
        Args:
            row: CSV row dictionary
            source_url: Source URL
            
        Returns:
            IOC dictionary or None
        """
        # Try common CSV column names
        value = row.get('value') or row.get('ioc') or row.get('indicator') or row.get('hash') or row.get('ip') or row.get('domain')
        if not value:
            return None
        
        ioc_type = row.get('type') or row.get('ioc_type') or 'unknown'
        
        return {
            'value': str(value),
            'type': str(ioc_type).lower(),
            'source': 'csv',
            'source_url': source_url,
            'first_seen': row.get('first_seen', '') or row.get('created', ''),
            'description': row.get('description', '') or row.get('comment', ''),
            'tags': [tag.strip() for tag in row.get('tags', '').split(',') if tag.strip()],
            'confidence': int(row.get('confidence', 50)) if row.get('confidence') else 50,
            'raw': row
        }

