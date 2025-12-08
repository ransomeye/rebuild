# Path and File Name : /home/ransomeye/rebuild/ransomeye_response/tools/signer/verify_playbook.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: CLI to verify playbook bundle signature

import argparse
import json
import base64
import tarfile
import shutil
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_bundle(bundle_path: Path, public_key_path: Path) -> bool:
    """
    Verify playbook bundle signature.
    
    Args:
        bundle_path: Path to playbook bundle
        public_key_path: Path to RSA public key
        
    Returns:
        True if signature is valid, False otherwise
    """
    bundle_path = Path(bundle_path)
    public_key_path = Path(public_key_path)
    
    if not bundle_path.exists():
        logger.error(f"Bundle not found: {bundle_path}")
        return False
    
    if not public_key_path.exists():
        logger.error(f"Public key not found: {public_key_path}")
        return False
    
    # Load public key
    with open(public_key_path, 'rb') as f:
        public_key = serialization.load_pem_public_key(
            f.read(),
            backend=default_backend()
        )
    
    # Extract bundle
    temp_dir = Path(f"/tmp/playbook_verify_{bundle_path.stem}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        with tarfile.open(bundle_path, 'r:gz') as tar:
            tar.extractall(temp_dir)
        
        # Load manifest and signature
        manifest_path = temp_dir / "manifest.json"
        signature_path = temp_dir / "manifest.sig"
        
        if not manifest_path.exists():
            logger.error("manifest.json not found in bundle")
            return False
        
        if not signature_path.exists():
            logger.error("manifest.sig not found in bundle")
            return False
        
        with open(manifest_path, 'rb') as f:
            manifest_content = f.read()
        
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
            logger.info("✓ Playbook signature is valid")
            return True
        except InvalidSignature:
            logger.error("✗ Playbook signature is invalid")
            return False
            
    except Exception as e:
        logger.error(f"Error verifying bundle: {e}")
        return False
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

def main():
    parser = argparse.ArgumentParser(description='Verify playbook bundle signature')
    parser.add_argument('--bundle', type=str, required=True,
                       help='Path to playbook bundle')
    parser.add_argument('--key', type=str, required=True,
                       help='Path to RSA public key')
    
    args = parser.parse_args()
    
    try:
        is_valid = verify_bundle(Path(args.bundle), Path(args.key))
        return 0 if is_valid else 1
    except Exception as e:
        logger.error(f"Error verifying bundle: {e}")
        return 1

if __name__ == "__main__":
    exit(main())

