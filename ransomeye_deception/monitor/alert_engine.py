# Path and File Name : /home/ransomeye/rebuild/ransomeye_deception/monitor/alert_engine.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Normalizes hits into Standard Alert JSON to send to Core

import os
import sys
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertEngine:
    """
    Alert engine for decoy interactions.
    Normalizes hits into standard alert format and sends to Core.
    """
    
    def __init__(self):
        """Initialize alert engine."""
        self.alert_api_url = os.environ.get(
            'ALERT_API_URL',
            'http://localhost:8004/api/alerts'
        )
        self.enabled = os.environ.get('ALERT_ENABLED', 'true').lower() == 'true'
        
        logger.info(f"Alert engine initialized (enabled: {self.enabled})")
    
    async def send_decoy_alert(self, decoy_id: str, event_type: str,
                               event_data: Dict[str, Any]) -> bool:
        """
        Send decoy interaction alert to Core.
        
        Args:
            decoy_id: Decoy ID
            event_type: Type of event (file_access, service_connection, etc.)
            event_data: Event data
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            logger.debug("Alerts disabled, skipping")
            return False
        
        try:
            # Build standard alert
            alert = self._build_alert(decoy_id, event_type, event_data)
            
            # Send to alert engine
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.alert_api_url,
                    json=alert,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Alert sent successfully: {decoy_id} - {event_type}")
                        return True
                    else:
                        logger.error(f"Failed to send alert: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return False
    
    def _build_alert(self, decoy_id: str, event_type: str,
                    event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build standard alert from decoy event.
        
        Args:
            decoy_id: Decoy ID
            event_type: Event type
            event_data: Event data
            
        Returns:
            Standard alert dictionary
        """
        # Map event types to severity
        severity_map = {
            'file_access': 'high',
            'file_modify': 'critical',
            'service_connection': 'high',
            'process_access': 'medium'
        }
        
        severity = severity_map.get(event_type, 'medium')
        
        # Build alert
        alert = {
            'source': 'deception_framework',
            'alert_type': 'decoy_interaction',
            'severity': severity,
            'title': f"Decoy Interaction Detected: {event_type}",
            'description': self._build_description(decoy_id, event_type, event_data),
            'timestamp': event_data.get('timestamp', datetime.utcnow().isoformat()),
            'metadata': {
                'decoy_id': decoy_id,
                'event_type': event_type,
                **event_data
            },
            'indicators': self._extract_indicators(event_type, event_data)
        }
        
        return alert
    
    def _build_description(self, decoy_id: str, event_type: str,
                          event_data: Dict[str, Any]) -> str:
        """
        Build alert description.
        
        Args:
            decoy_id: Decoy ID
            event_type: Event type
            event_data: Event data
            
        Returns:
            Description string
        """
        if event_type == 'file_access':
            path = event_data.get('path', 'unknown')
            return f"Honeyfile accessed: {path} (Decoy: {decoy_id})"
        elif event_type == 'file_modify':
            path = event_data.get('path', 'unknown')
            return f"Honeyfile modified: {path} (Decoy: {decoy_id})"
        elif event_type == 'service_connection':
            client_ip = event_data.get('client_ip', 'unknown')
            port = event_data.get('port', 'unknown')
            return f"Connection to honeypot service from {client_ip}:{port} (Decoy: {decoy_id})"
        else:
            return f"Decoy interaction detected: {event_type} (Decoy: {decoy_id})"
    
    def _extract_indicators(self, event_type: str,
                           event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract threat indicators from event.
        
        Args:
            event_type: Event type
            event_data: Event data
            
        Returns:
            Indicators dictionary
        """
        indicators = {}
        
        if event_type == 'file_access' or event_type == 'file_modify':
            indicators['file_path'] = event_data.get('path')
            indicators['file_hash'] = event_data.get('hash')
        
        elif event_type == 'service_connection':
            indicators['source_ip'] = event_data.get('client_ip')
            indicators['destination_port'] = event_data.get('port')
            indicators['protocol'] = event_data.get('protocol', 'tcp')
        
        return indicators

