# Path and File Name : /home/ransomeye/rebuild/ransomeye_correlation/engine/entity_extractor.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Parses Alert JSON and extracts entities (Host, IP, File, User) with deterministic IDs

import hashlib
import json
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EntityExtractor:
    """
    Extracts entities from alerts and generates deterministic IDs.
    """
    
    def __init__(self):
        """Initialize entity extractor."""
        pass
    
    def extract(self, alert: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract entities from alert.
        
        Args:
            alert: Alert dictionary
            
        Returns:
            List of entity dictionaries
        """
        entities = []
        
        # Extract Host entities
        if 'host' in alert:
            host_value = alert['host']
            if isinstance(host_value, str) and host_value:
                entities.append(self._create_entity('Host', host_value))
        
        if 'hostname' in alert:
            hostname_value = alert['hostname']
            if isinstance(hostname_value, str) and hostname_value:
                entities.append(self._create_entity('Host', hostname_value))
        
        # Extract IP entities
        if 'src_ip' in alert:
            ip_value = alert['src_ip']
            if isinstance(ip_value, str) and ip_value:
                entities.append(self._create_entity('IP', ip_value))
        
        if 'dst_ip' in alert:
            ip_value = alert['dst_ip']
            if isinstance(ip_value, str) and ip_value:
                entities.append(self._create_entity('IP', ip_value))
        
        if 'ip' in alert:
            ip_value = alert['ip']
            if isinstance(ip_value, str) and ip_value:
                entities.append(self._create_entity('IP', ip_value))
        
        # Extract File entities
        if 'file_path' in alert:
            file_value = alert['file_path']
            if isinstance(file_value, str) and file_value:
                entities.append(self._create_entity('File', file_value))
        
        if 'filename' in alert:
            file_value = alert['filename']
            if isinstance(file_value, str) and file_value:
                entities.append(self._create_entity('File', file_value))
        
        # Extract User entities
        if 'user' in alert:
            user_value = alert['user']
            if isinstance(user_value, str) and user_value:
                entities.append(self._create_entity('User', user_value))
        
        if 'username' in alert:
            user_value = alert['username']
            if isinstance(user_value, str) and user_value:
                entities.append(self._create_entity('User', user_value))
        
        # Extract from nested structures
        if 'metadata' in alert and isinstance(alert['metadata'], dict):
            metadata = alert['metadata']
            if 'host' in metadata:
                entities.append(self._create_entity('Host', metadata['host']))
            if 'ip' in metadata:
                entities.append(self._create_entity('IP', metadata['ip']))
            if 'user' in metadata:
                entities.append(self._create_entity('User', metadata['user']))
        
        logger.debug(f"Extracted {len(entities)} entities from alert")
        return entities
    
    def _create_entity(self, entity_type: str, value: str) -> Dict[str, Any]:
        """
        Create entity with deterministic ID.
        
        Args:
            entity_type: Type of entity (Host, IP, File, User)
            value: Entity value
            
        Returns:
            Entity dictionary
        """
        # Generate deterministic ID: sha256(type + value)
        entity_id = self._generate_id(entity_type, value)
        
        return {
            'id': entity_id,
            'type': entity_type,
            'value': value,
            'label': f"{entity_type}:{value}"
        }
    
    def _generate_id(self, entity_type: str, value: str) -> str:
        """
        Generate deterministic ID using SHA256.
        
        Args:
            entity_type: Type of entity
            value: Entity value
            
        Returns:
            Deterministic ID (hex digest)
        """
        # Normalize input
        normalized = f"{entity_type}:{value}".lower().strip()
        
        # Generate SHA256 hash
        hash_obj = hashlib.sha256(normalized.encode('utf-8'))
        return hash_obj.hexdigest()

