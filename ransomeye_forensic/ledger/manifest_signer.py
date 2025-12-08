# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/ledger/manifest_signer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Signs ledger entries using RSA private key from EVIDENCE_SIGN_KEY_PATH

import os
import json
import base64
from pathlib import Path
from typing import Dict
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManifestSigner:
    """Signs ledger entries using RSA private key."""
    
    def __init__(self, private_key_path: str = None):
        """
        Initialize manifest signer.
        
        Args:
            private_key_path: Path to RSA private key
        """
        self.private_key_path = Path(private_key_path or os.environ.get(
            'EVIDENCE_SIGN_KEY_PATH',
            '/home/ransomeye/rebuild/certs/evidence_sign_private.pem'
        ))
        self.private_key = self._load_or_generate_key()
    
    def _load_or_generate_key(self):
        """Load or generate RSA private key."""
        if self.private_key_path.exists():
            try:
                with open(self.private_key_path, 'rb') as f:
                    return serialization.load_pem_private_key(
                        f.read(),
                        password=None,
                        backend=default_backend()
                    )
            except Exception as e:
                logger.warning(f"Failed to load private key: {e}, generating new key")
        
        # Generate new key (RSA-4096)
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )
        
        # Save private key
        self.private_key_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.private_key_path, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        os.chmod(self.private_key_path, 0o600)
        
        logger.info(f"Generated new evidence signing key: {self.private_key_path}")
        return private_key
    
    def sign_entry(self, entry: Dict) -> str:
        """
        Sign a ledger entry.
        
        Args:
            entry: Entry dictionary
            
        Returns:
            Base64-encoded signature
        """
        # Create signature of entry content
        entry_content = json.dumps(entry, sort_keys=True).encode()
        
        signature = self.private_key.sign(
            entry_content,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return base64.b64encode(signature).decode('utf-8')
    
    def verify_entry(self, entry: Dict, signature: str) -> bool:
        """
        Verify signature of a ledger entry.
        
        Args:
            entry: Entry dictionary
            signature: Base64-encoded signature
            
        Returns:
            True if signature is valid, False otherwise
        """
        # Get public key
        public_key = self.private_key.public_key()
        
        # Decode signature
        signature_bytes = base64.b64decode(signature)
        
        # Create entry content
        entry_content = json.dumps(entry, sort_keys=True).encode()
        
        try:
            public_key.verify(
                signature_bytes,
                entry_content,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False

