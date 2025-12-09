# Path and File Name : /home/ransomeye/rebuild/ransomeye_orchestrator/bundle/signer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Signs manifest using RSA private key

import os
import json
import base64
import logging
from pathlib import Path
from typing import Dict, Any
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class ManifestSigner:
    """Signs manifest using RSA private key."""
    
    def __init__(self, key_path: str = None):
        """
        Initialize signer.
        
        Args:
            key_path: Path to private key (default: ORCH_SIGN_KEY_PATH env var)
        """
        if key_path is None:
            key_path = os.environ.get('ORCH_SIGN_KEY_PATH', '')
        
        if not key_path or not os.path.exists(key_path):
            raise ValueError(f"Sign key not found: {key_path}")
        
        self.key_path = key_path
        self.private_key = self._load_private_key(key_path)
    
    def _load_private_key(self, key_path: str):
        """Load RSA private key from file."""
        try:
            with open(key_path, 'rb') as f:
                private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
            logger.info(f"Private key loaded from {key_path}")
            return private_key
        except Exception as e:
            logger.error(f"Failed to load private key: {e}")
            raise
    
    def sign_manifest(self, manifest: Dict[str, Any]) -> str:
        """
        Sign manifest and return signature.
        
        Args:
            manifest: Manifest dictionary
        
        Returns:
            Base64-encoded signature
        """
        # Create canonical JSON (sorted keys, no whitespace)
        manifest_json = json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode('utf-8')
        
        # Sign with RSA-PSS
        signature = self.private_key.sign(
            manifest_json,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Encode signature
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        logger.info("Manifest signed successfully")
        return signature_b64
    
    def save_signature(self, manifest: Dict[str, Any], output_path: Path):
        """
        Sign manifest and save signature file.
        
        Args:
            manifest: Manifest dictionary
            output_path: Path to save signature file
        """
        signature = self.sign_manifest(manifest)
        
        signature_data = {
            "manifest_hash": manifest.get('manifest_hash', ''),
            "signature": signature,
            "algorithm": "RSA-PSS-SHA256",
            "key_id": os.path.basename(self.key_path),
            "signed_at": manifest.get('created_at', '')
        }
        
        with open(output_path, 'w') as f:
            json.dump(signature_data, f, indent=2)
        
        logger.info(f"Signature saved to {output_path}")

