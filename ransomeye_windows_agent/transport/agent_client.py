# Path and File Name : /home/ransomeye/rebuild/ransomeye_windows_agent/transport/agent_client.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: mTLS client using requests with certificate and key authentication for Windows

import os
import requests
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentClient:
    """mTLS client for communicating with Core API."""
    
    def __init__(self):
        """Initialize mTLS client."""
        self.core_api_url = os.environ.get('CORE_API_URL', 'https://localhost:8443')
        
        # Windows-specific certificate paths
        cert_base = os.path.join(
            os.environ.get('PROGRAMDATA', 'C:\\ProgramData'),
            'RansomEye',
            'certs'
        )
        
        self.cert_path = os.environ.get(
            'AGENT_CERT_PATH',
            os.path.join(cert_base, 'agent.crt')
        )
        self.key_path = os.environ.get(
            'AGENT_KEY_PATH',
            os.path.join(cert_base, 'agent.key')
        )
        self.ca_cert_path = os.environ.get(
            'CA_CERT_PATH',
            os.path.join(cert_base, 'ca.crt')
        )
        
        # Verify certificates exist
        if not Path(self.cert_path).exists():
            logger.warning(f"Certificate not found: {self.cert_path}")
        if not Path(self.key_path).exists():
            logger.warning(f"Key not found: {self.key_path}")
        
        logger.info(f"Agent client initialized: {self.core_api_url}")
    
    def post(self, endpoint: str, data: Dict[str, Any], timeout: int = 30) -> Optional[Dict[str, Any]]:
        """
        POST request to Core API with mTLS.
        
        Args:
            endpoint: API endpoint path
            data: Request data
            timeout: Request timeout in seconds
            
        Returns:
            Response JSON or None on error
        """
        url = f"{self.core_api_url}{endpoint}"
        
        try:
            # Prepare certificates
            cert = None
            verify = True
            
            if Path(self.cert_path).exists() and Path(self.key_path).exists():
                cert = (self.cert_path, self.key_path)
            
            if Path(self.ca_cert_path).exists():
                verify = self.ca_cert_path
            elif not Path(self.ca_cert_path).exists():
                verify = False  # Allow self-signed certs in dev
            
            response = requests.post(
                url,
                json=data,
                cert=cert,
                verify=verify,
                timeout=timeout
            )
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
    
    def get(self, endpoint: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """
        GET request to Core API with mTLS.
        
        Args:
            endpoint: API endpoint path
            timeout: Request timeout in seconds
            
        Returns:
            Response JSON or None on error
        """
        url = f"{self.core_api_url}{endpoint}"
        
        try:
            cert = None
            verify = True
            
            if Path(self.cert_path).exists() and Path(self.key_path).exists():
                cert = (self.cert_path, self.key_path)
            
            if Path(self.ca_cert_path).exists():
                verify = self.ca_cert_path
            elif not Path(self.ca_cert_path).exists():
                verify = False
            
            response = requests.get(
                url,
                cert=cert,
                verify=verify,
                timeout=timeout
            )
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None

