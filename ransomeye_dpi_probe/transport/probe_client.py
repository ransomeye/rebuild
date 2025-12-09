# Path and File Name : /home/ransomeye/rebuild/ransomeye_dpi_probe/transport/probe_client.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: mTLS client for communicating with Core API

import os
import requests
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProbeClient:
    """mTLS client for DPI Probe to Core API communication."""
    
    def __init__(self):
        """Initialize mTLS client."""
        self.core_api_url = os.environ.get('CORE_API_URL', 'https://localhost:8443')
        self.cert_path = os.environ.get('PROBE_CERT_PATH', '/etc/ransomeye-probe/certs/probe.crt')
        self.key_path = os.environ.get('PROBE_KEY_PATH', '/etc/ransomeye-probe/certs/probe.key')
        self.ca_cert_path = os.environ.get('CA_CERT_PATH', '/etc/ransomeye-probe/certs/ca.crt')
        
        # Verify certificates exist
        if not Path(self.cert_path).exists():
            logger.warning(f"Certificate not found: {self.cert_path}")
        if not Path(self.key_path).exists():
            logger.warning(f"Key not found: {self.key_path}")
        
        logger.info(f"Probe client initialized: {self.core_api_url}")
    
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
    
    def upload_file(self, endpoint: str, file_path: str, metadata: Dict[str, Any] = None,
                   timeout: int = 300) -> Optional[Dict[str, Any]]:
        """
        Upload file with metadata.
        
        Args:
            endpoint: Upload endpoint
            file_path: Path to file to upload
            metadata: Optional metadata dictionary
            timeout: Request timeout in seconds
            
        Returns:
            Response JSON with receipt or None on error
        """
        url = f"{self.core_api_url}{endpoint}"
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            logger.error(f"File not found: {file_path}")
            return None
        
        try:
            cert = None
            verify = True
            
            if Path(self.cert_path).exists() and Path(self.key_path).exists():
                cert = (self.cert_path, self.key_path)
            
            if Path(self.ca_cert_path).exists():
                verify = self.ca_cert_path
            else:
                verify = False
            
            with open(file_path, 'rb') as f:
                files = {'file': (file_path_obj.name, f, 'application/octet-stream')}
                data = metadata or {}
                
                response = requests.post(
                    url,
                    files=files,
                    data=data,
                    cert=cert,
                    verify=verify,
                    timeout=timeout
                )
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Upload failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None

