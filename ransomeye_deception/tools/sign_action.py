# Path and File Name : /home/ransomeye/rebuild/ransomeye_deception/tools/sign_action.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Signs placement manifests for audit and integrity

import os
import sys
import json
import hashlib
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ActionSigner:
    """
    Signs placement and rotation actions for audit trail.
    """
    
    def __init__(self):
        """Initialize action signer."""
        # In production, use proper cryptographic signing
        # For now, use SHA256 hash as signature
        self.signing_key = os.environ.get('DECEPTION_SIGNING_KEY', 'default_key_change_in_production')
        logger.info("Action signer initialized")
    
    def sign_action(self, action_type: str, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign an action.
        
        Args:
            action_type: Type of action (deploy, rotate, remove)
            action_data: Action data dictionary
            
        Returns:
            Signed action manifest
        """
        # Create manifest
        manifest = {
            'action_type': action_type,
            'action_data': action_data,
            'timestamp': datetime.utcnow().isoformat(),
            'signer': 'deception_framework'
        }
        
        # Calculate signature
        manifest_str = json.dumps(manifest, sort_keys=True)
        signature = self._calculate_signature(manifest_str)
        
        # Add signature to manifest
        manifest['signature'] = signature
        
        return manifest
    
    def _calculate_signature(self, data: str) -> str:
        """
        Calculate signature for data.
        
        Args:
            data: Data to sign
            
        Returns:
            Signature string
        """
        # In production, use HMAC-SHA256 with proper key management
        combined = f"{self.signing_key}:{data}"
        signature = hashlib.sha256(combined.encode('utf-8')).hexdigest()
        return signature
    
    def verify_signature(self, manifest: Dict[str, Any]) -> bool:
        """
        Verify manifest signature.
        
        Args:
            manifest: Manifest dictionary
            
        Returns:
            True if signature is valid
        """
        try:
            signature = manifest.pop('signature')
            manifest_str = json.dumps(manifest, sort_keys=True)
            expected_signature = self._calculate_signature(manifest_str)
            manifest['signature'] = signature  # Restore
            
            return signature == expected_signature
        except Exception as e:
            logger.error(f"Error verifying signature: {e}")
            return False

