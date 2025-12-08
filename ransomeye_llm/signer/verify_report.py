# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm/signer/verify_report.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Verification logic for signed reports

import json
import base64
import hashlib
from pathlib import Path
from typing import Tuple
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_report_signature(manifest_path: Path, signature_path: Path, 
                           public_key_path: Path) -> bool:
    """
    Verify signature of report manifest.
    
    Args:
        manifest_path: Path to manifest.json
        signature_path: Path to manifest.sig
        public_key_path: Path to RSA public key
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not manifest_path.exists():
        logger.error(f"Manifest file not found: {manifest_path}")
        return False
    
    if not signature_path.exists():
        logger.error(f"Signature file not found: {signature_path}")
        return False
    
    if not public_key_path.exists():
        logger.error(f"Public key file not found: {public_key_path}")
        return False
    
    try:
        # Load public key
        with open(public_key_path, 'rb') as f:
            public_key = serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )
        
        # Read manifest content
        with open(manifest_path, 'rb') as f:
            manifest_content = f.read()
        
        # Read signature
        with open(signature_path, 'r') as f:
            signature_b64 = f.read().strip()
            signature = base64.b64decode(signature_b64)
        
        # Verify signature
        try:
            public_key.verify(
                signature,
                manifest_content,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            logger.info("✓ Report signature is valid")
            return True
        except InvalidSignature:
            logger.error("✗ Report signature is invalid")
            return False
            
    except Exception as e:
        logger.error(f"Error verifying signature: {e}")
        return False

def verify_pdf_hash(manifest_path: Path, pdf_path: Path) -> bool:
    """
    Verify PDF hash matches manifest.
    
    Args:
        manifest_path: Path to manifest.json
        pdf_path: Path to PDF file
        
    Returns:
        True if hash matches, False otherwise
    """
    if not manifest_path.exists():
        return False
    
    if not pdf_path.exists():
        return False
    
    try:
        # Load manifest
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        expected_hash = manifest.get('pdf_hash')
        if not expected_hash:
            return False
        
        # Calculate actual hash
        sha256_hash = hashlib.sha256()
        with open(pdf_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        actual_hash = sha256_hash.hexdigest()
        
        if actual_hash == expected_hash:
            logger.info("✓ PDF hash matches manifest")
            return True
        else:
            logger.error("✗ PDF hash does not match manifest")
            return False
            
    except Exception as e:
        logger.error(f"Error verifying PDF hash: {e}")
        return False

def verify_report(manifest_path: Path, signature_path: Path, pdf_path: Path,
                 public_key_path: Path) -> Tuple[bool, bool]:
    """
    Verify complete report (signature and hash).
    
    Args:
        manifest_path: Path to manifest.json
        signature_path: Path to manifest.sig
        pdf_path: Path to PDF file
        public_key_path: Path to RSA public key
        
    Returns:
        Tuple of (signature_valid, hash_valid)
    """
    sig_valid = verify_report_signature(manifest_path, signature_path, public_key_path)
    hash_valid = verify_pdf_hash(manifest_path, pdf_path)
    
    return sig_valid, hash_valid

