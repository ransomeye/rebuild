# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/tools/verify_signature.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Verifies RSA-4096 signature on summary

import os
from pathlib import Path
from typing import Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import cryptography
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("cryptography not available. Install: pip install cryptography")


def verify_signature(summary_text: str, signature_hex: str, public_key_path: str = None) -> Dict:
    """
    Verify signature on summary.
    
    Args:
        summary_text: Summary text
        signature_hex: Signature in hex format
        public_key_path: Path to public key
        
    Returns:
        Verification result
    """
    if not CRYPTO_AVAILABLE:
        logger.warning("Cryptography not available. Returning mock verification.")
        return {
            'valid': False,
            'error': 'Cryptography not available'
        }
    
    if public_key_path is None:
        public_key_path = os.environ.get(
            'VERIFY_KEY_PATH',
            '/home/ransomeye/rebuild/certs/summary_sign_public.pem'
        )
    
    try:
        # Load public key
        with open(public_key_path, 'rb') as f:
            public_key = serialization.load_pem_public_key(f.read())
        
        # Verify
        signature = bytes.fromhex(signature_hex)
        public_key.verify(
            signature,
            summary_text.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return {
            'valid': True,
            'message': 'Signature verified'
        }
    
    except Exception as e:
        return {
            'valid': False,
            'error': str(e)
        }

