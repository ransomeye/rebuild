# Path and File Name : /home/ransomeye/rebuild/ransomeye_linux_agent/security/key_manager.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Checks permissions of keys and certificates (must be 0600)

import os
import stat
from pathlib import Path
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KeyManager:
    """Manages key and certificate permissions."""
    
    REQUIRED_PERMISSIONS = 0o600  # rw------- (owner read/write only)
    
    def __init__(self):
        """Initialize key manager."""
        logger.info("Key manager initialized")
    
    def check_key_permissions(self, key_path: str) -> bool:
        """
        Check if key file has correct permissions (0600).
        
        Args:
            key_path: Path to key file
            
        Returns:
            True if permissions are correct
        """
        try:
            key_file = Path(key_path)
            
            if not key_file.exists():
                logger.warning(f"Key file not found: {key_path}")
                return False
            
            file_stat = key_file.stat()
            current_perms = stat.filemode(file_stat.st_mode)
            numeric_perms = stat.S_IMODE(file_stat.st_mode)
            
            if numeric_perms != self.REQUIRED_PERMISSIONS:
                logger.error(
                    f"Key file has incorrect permissions: {key_path}\n"
                    f"  Current: {current_perms} ({oct(numeric_perms)})\n"
                    f"  Required: {stat.filemode(self.REQUIRED_PERMISSIONS)} ({oct(self.REQUIRED_PERMISSIONS)})"
                )
                return False
            
            logger.debug(f"Key permissions OK: {key_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error checking key permissions: {e}")
            return False
    
    def fix_key_permissions(self, key_path: str) -> bool:
        """
        Fix key file permissions to 0600.
        
        Args:
            key_path: Path to key file
            
        Returns:
            True if successful
        """
        try:
            key_file = Path(key_path)
            
            if not key_file.exists():
                logger.error(f"Key file not found: {key_path}")
                return False
            
            os.chmod(key_file, self.REQUIRED_PERMISSIONS)
            logger.info(f"Fixed permissions for: {key_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error fixing key permissions: {e}")
            return False
    
    def validate_all_keys(self) -> Dict[str, bool]:
        """
        Validate all required keys and certificates.
        
        Returns:
            Dictionary of key paths and validation results
        """
        results = {}
        
        # Check agent certificate and key
        cert_path = os.environ.get('AGENT_CERT_PATH', '/etc/ransomeye-agent/certs/agent.crt')
        key_path = os.environ.get('AGENT_KEY_PATH', '/etc/ransomeye-agent/certs/agent.key')
        ca_cert_path = os.environ.get('CA_CERT_PATH', '/etc/ransomeye-agent/certs/ca.crt')
        update_key_path = os.environ.get('AGENT_UPDATE_KEY_PATH', '/etc/ransomeye-agent/keys/update_key.pub')
        
        # Only check key files (not certificates)
        key_files = [key_path, update_key_path]
        
        for key_file in key_files:
            if Path(key_file).exists():
                results[key_file] = self.check_key_permissions(key_file)
        
        return results

