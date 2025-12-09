# Path and File Name : /home/ransomeye/rebuild/ransomeye_linux_agent/security/config_validator.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Validates environment variables and configuration at startup

import os
from pathlib import Path
from typing import List, bool
import logging

from .key_manager import KeyManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validates agent configuration."""
    
    REQUIRED_ENV_VARS = [
        'CORE_API_URL',
    ]
    
    OPTIONAL_ENV_VARS = [
        'AGENT_CERT_PATH',
        'AGENT_KEY_PATH',
        'CA_CERT_PATH',
        'AGENT_UPDATE_KEY_PATH',
        'BUFFER_DIR',
        'MODEL_PATH',
        'DETECTION_THRESHOLD',
        'HEARTBEAT_INTERVAL',
        'COLLECTION_INTERVAL',
        'UPLOAD_BATCH_SIZE',
        'MONITOR_DIRS',
        'AGENT_METRICS_PORT'
    ]
    
    def __init__(self):
        """Initialize config validator."""
        self.key_manager = KeyManager()
        self.errors = []
        self.warnings = []
        logger.info("Config validator initialized")
    
    def validate(self) -> bool:
        """
        Validate configuration.
        
        Returns:
            True if valid, False otherwise
        """
        self.errors = []
        self.warnings = []
        
        # Check required environment variables
        for var in self.REQUIRED_ENV_VARS:
            if not os.environ.get(var):
                self.errors.append(f"Required environment variable not set: {var}")
        
        # Check key permissions
        key_results = self.key_manager.validate_all_keys()
        for key_path, is_valid in key_results.items():
            if not is_valid:
                self.errors.append(f"Key file has incorrect permissions: {key_path}")
        
        # Check buffer directory
        buffer_dir = os.environ.get('BUFFER_DIR', '/var/lib/ransomeye-agent/buffer')
        buffer_path = Path(buffer_dir)
        if not buffer_path.exists():
            try:
                buffer_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created buffer directory: {buffer_dir}")
            except Exception as e:
                self.errors.append(f"Cannot create buffer directory: {buffer_dir} - {e}")
        
        # Check model path (warning if not found)
        model_path = os.environ.get('MODEL_PATH', '/opt/ransomeye-agent/models/detector_model.pkl')
        if not Path(model_path).exists():
            self.warnings.append(f"Model file not found: {model_path} (will use default)")
        
        # Log results
        if self.errors:
            for error in self.errors:
                logger.error(error)
        
        if self.warnings:
            for warning in self.warnings:
                logger.warning(warning)
        
        if not self.errors:
            logger.info("Configuration validation passed")
            return True
        else:
            logger.error("Configuration validation failed")
            return False
    
    def get_errors(self) -> List[str]:
        """Get list of validation errors."""
        return self.errors
    
    def get_warnings(self) -> List[str]:
        """Get list of validation warnings."""
        return self.warnings

