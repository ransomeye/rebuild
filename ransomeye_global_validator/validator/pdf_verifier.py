# Path and File Name : /home/ransomeye/rebuild/ransomeye_global_validator/validator/pdf_verifier.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Verifies cryptographic signatures on PDF validation reports

import os
from pathlib import Path
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFVerifier:
    """Verifies cryptographic signatures on PDF reports."""
    
    def __init__(self):
        """Initialize PDF verifier with public key path."""
        self.public_key_path = os.environ.get(
            'VALIDATOR_PUBLIC_KEY_PATH',
            '/home/ransomeye/rebuild/ransomeye_global_validator/keys/sign_key.pub'
        )
        self.public_key = None
        self._load_public_key()
        logger.info("PDF verifier initialized")
    
    def _load_public_key(self):
        """Load RSA public key for verification."""
        try:
            key_path = Path(self.public_key_path)
            if key_path.exists():
                with open(key_path, 'rb') as f:
                    self.public_key = RSA.import_key(f.read())
                logger.info(f"Public key loaded from {self.public_key_path}")
            else:
                logger.warning(f"Public key not found at {self.public_key_path}")
        except Exception as e:
            logger.error(f"Failed to load public key: {e}")
    
    def verify_pdf(self, pdf_path: str) -> dict:
        """
        Verify PDF signature.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Verification result
        """
        if not self.public_key:
            return {
                "verified": False,
                "error": "Public key not loaded"
            }
        
        sig_path = pdf_path + '.sig'
        sig_meta_path = pdf_path + '.sig.meta'
        
        if not Path(sig_path).exists():
            return {
                "verified": False,
                "error": "Signature file not found"
            }
        
        try:
            # Read PDF content
            with open(pdf_path, 'rb') as f:
                pdf_content = f.read()
            
            # Create hash
            pdf_hash = SHA256.new(pdf_content)
            
            # Read signature
            with open(sig_path, 'rb') as f:
                signature = f.read()
            
            # Verify signature
            try:
                pkcs1_15.new(self.public_key).verify(pdf_hash, signature)
                
                # Read metadata if available
                metadata = {}
                if Path(sig_meta_path).exists():
                    with open(sig_meta_path, 'r') as f:
                        for line in f:
                            if '=' in line:
                                key, value = line.strip().split('=', 1)
                                metadata[key] = value
                
                logger.info(f"PDF signature verified: {pdf_path}")
                return {
                    "verified": True,
                    "pdf_hash_sha256": pdf_hash.hexdigest(),
                    "metadata": metadata
                }
            
            except (ValueError, TypeError) as e:
                logger.error(f"Signature verification failed: {e}")
                return {
                    "verified": False,
                    "error": f"Signature verification failed: {str(e)}"
                }
        
        except Exception as e:
            logger.error(f"Error verifying PDF: {e}")
            return {
                "verified": False,
                "error": str(e)
            }

