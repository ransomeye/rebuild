# Path and File Name : /home/ransomeye/rebuild/ransomeye_global_validator/chain/manifest_signer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Signs run manifest using RSA private key

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ManifestSigner:
    """Signs validation run manifests."""
    
    def __init__(self):
        """Initialize manifest signer."""
        self.sign_key_path = os.environ.get(
            'VALIDATOR_SIGN_KEY_PATH',
            '/home/ransomeye/rebuild/ransomeye_global_validator/keys/sign_key.pem'
        )
        self.private_key = None
        self._load_private_key()
        logger.info("Manifest signer initialized")
    
    def _load_private_key(self):
        """Load RSA private key."""
        try:
            key_path = Path(self.sign_key_path)
            if key_path.exists():
                with open(key_path, 'rb') as f:
                    self.private_key = RSA.import_key(f.read())
                logger.info(f"Private key loaded from {self.sign_key_path}")
            else:
                logger.warning(f"Signing key not found at {self.sign_key_path}")
        except Exception as e:
            logger.error(f"Failed to load private key: {e}")
    
    def sign_manifest(self, manifest_path: str) -> str:
        """
        Sign manifest file.
        
        Args:
            manifest_path: Path to manifest JSON file
            
        Returns:
            Path to signed manifest file
        """
        if not self.private_key:
            logger.warning("Private key not available, manifest will not be signed")
            return manifest_path
        
        try:
            # Read manifest
            with open(manifest_path, 'r') as f:
                manifest_data = json.load(f)
            
            # Create hash of manifest content
            manifest_json = json.dumps(manifest_data, sort_keys=True)
            manifest_hash = SHA256.new(manifest_json.encode())
            
            # Sign hash
            signature = pkcs1_15.new(self.private_key).sign(manifest_hash)
            
            # Add signature to manifest
            manifest_data["signature"] = {
                "signature_hex": signature.hex(),
                "signed_at": datetime.utcnow().isoformat(),
                "signer": "RansomEye Global Validator"
            }
            
            # Save signed manifest
            signed_path = manifest_path.replace('.json', '.signed.json')
            with open(signed_path, 'w') as f:
                json.dump(manifest_data, f, indent=2)
            
            logger.info(f"Manifest signed: {signed_path}")
            return signed_path
        
        except Exception as e:
            logger.error(f"Failed to sign manifest: {e}")
            return manifest_path

