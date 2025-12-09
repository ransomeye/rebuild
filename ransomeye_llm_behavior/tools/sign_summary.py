# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/tools/sign_summary.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Signs summary with RSA-4096 signature

import os
import hashlib
from pathlib import Path
from typing import Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import cryptography
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("cryptography not available. Install: pip install cryptography")


def sign_summary(summary_text: str, private_key_path: str = None) -> Dict:
    """
    Sign summary with RSA-4096.
    
    Args:
        summary_text: Summary text to sign
        private_key_path: Path to private key
        
    Returns:
        Dictionary with signature and metadata
    """
    if not CRYPTO_AVAILABLE:
        logger.warning("Cryptography not available. Returning mock signature.")
        return {
            'signature': 'mock_signature',
            'algorithm': 'RSA-4096',
            'hash': hashlib.sha256(summary_text.encode()).hexdigest()
        }
    
    if private_key_path is None:
        private_key_path = os.environ.get(
            'SIGN_KEY_PATH',
            '/home/ransomeye/rebuild/certs/summary_sign_private.pem'
        )
    
    try:
        # Load private key
        with open(private_key_path, 'rb') as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
        
        # Sign
        signature = private_key.sign(
            summary_text.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return {
            'signature': signature.hex(),
            'algorithm': 'RSA-4096',
            'hash': hashlib.sha256(summary_text.encode()).hexdigest()
        }
    
    except Exception as e:
        logger.error(f"Error signing summary: {e}")
        return {
            'signature': None,
            'error': str(e)
        }

