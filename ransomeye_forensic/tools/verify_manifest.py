# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/tools/verify_manifest.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: CLI tool to verify evidence manifest signature and ledger chain integrity

import argparse
import json
import base64
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ledger.evidence_ledger import EvidenceLedger
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_manifest_signature(manifest_path: Path, signature_path: Path, public_key_path: Path) -> bool:
    """
    Verify signature of manifest.json.
    
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
            logger.info("✓ Manifest signature is valid")
            return True
        except InvalidSignature:
            logger.error("✗ Manifest signature is invalid")
            return False
            
    except Exception as e:
        logger.error(f"Error verifying signature: {e}")
        return False

def verify_ledger_chain(ledger_path: Path) -> bool:
    """
    Verify ledger chain integrity.
    
    Args:
        ledger_path: Path to evidence ledger
        
    Returns:
        True if chain is valid, False otherwise
    """
    ledger = EvidenceLedger(ledger_path=str(ledger_path))
    return ledger.verify_chain()

def main():
    parser = argparse.ArgumentParser(description='Verify evidence manifest and ledger')
    parser.add_argument('--manifest', type=str, default=None,
                       help='Path to manifest.json (optional)')
    parser.add_argument('--signature', type=str, default=None,
                       help='Path to manifest.sig (optional)')
    parser.add_argument('--key', type=str, default=None,
                       help='Path to RSA public key (optional)')
    parser.add_argument('--ledger', type=str, required=True,
                       help='Path to evidence ledger')
    
    args = parser.parse_args()
    
    all_valid = True
    
    # Verify ledger chain
    logger.info("Verifying ledger chain...")
    if verify_ledger_chain(Path(args.ledger)):
        logger.info("✓ Ledger chain is valid")
    else:
        logger.error("✗ Ledger chain verification failed")
        all_valid = False
    
    # Verify manifest signature if provided
    if args.manifest and args.signature and args.key:
        logger.info("Verifying manifest signature...")
        if verify_manifest_signature(
            Path(args.manifest),
            Path(args.signature),
            Path(args.key)
        ):
            logger.info("✓ Manifest signature is valid")
        else:
            logger.error("✗ Manifest signature verification failed")
            all_valid = False
    
    return 0 if all_valid else 1

if __name__ == "__main__":
    exit(main())

