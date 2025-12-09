# Path and File Name : /home/ransomeye/rebuild/ransomeye_windows_agent/security/config_validator.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Validates agent configuration and environment variables

import os
from pathlib import Path
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validates agent configuration."""
    
    def __init__(self):
        """Initialize config validator."""
        self.errors = []
        self.warnings = []
    
    def validate(self) -> bool:
        """
        Validate configuration.
        
        Returns:
            True if valid
        """
        self.errors = []
        self.warnings = []
        
        # Check required environment variables
        self._check_required_env_vars()
        
        # Check paths
        self._check_paths()
        
        # Check certificates
        self._check_certificates()
        
        # Log results
        if self.errors:
            for error in self.errors:
                logger.error(f"Config error: {error}")
        
        if self.warnings:
            for warning in self.warnings:
                logger.warning(f"Config warning: {warning}")
        
        return len(self.errors) == 0
    
    def _check_required_env_vars(self):
        """Check required environment variables."""
        required = ['CORE_API_URL']
        optional = [
            'AGENT_CERT_PATH', 'AGENT_KEY_PATH', 'CA_CERT_PATH',
            'BUFFER_DIR', 'MODEL_PATH', 'HEARTBEAT_INTERVAL_SEC',
            'UPLOAD_BATCH_SIZE', 'AGENT_MAX_BUFFER_MB'
        ]
        
        for var in required:
            if not os.environ.get(var):
                self.errors.append(f"Required environment variable not set: {var}")
        
        for var in optional:
            if not os.environ.get(var):
                self.warnings.append(f"Optional environment variable not set: {var}")
    
    def _check_paths(self):
        """Check that paths exist or can be created."""
        # Buffer directory
        buffer_dir = os.environ.get('BUFFER_DIR')
        if buffer_dir:
            try:
                Path(buffer_dir).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.errors.append(f"Cannot create buffer directory {buffer_dir}: {e}")
        
        # Model directory
        model_path = os.environ.get('MODEL_PATH')
        if model_path:
            model_dir = Path(model_path).parent
            try:
                model_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.warnings.append(f"Cannot create model directory {model_dir}: {e}")
    
    def _check_certificates(self):
        """Check certificate files."""
        cert_path = os.environ.get('AGENT_CERT_PATH')
        key_path = os.environ.get('AGENT_KEY_PATH')
        ca_cert_path = os.environ.get('CA_CERT_PATH')
        
        if cert_path and not Path(cert_path).exists():
            self.warnings.append(f"Certificate not found: {cert_path}")
        
        if key_path and not Path(key_path).exists():
            self.warnings.append(f"Key not found: {key_path}")
        
        if ca_cert_path and not Path(ca_cert_path).exists():
            self.warnings.append(f"CA certificate not found: {ca_cert_path}")

