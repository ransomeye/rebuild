# Path and File Name : /home/ransomeye/rebuild/ransomeye_response/tools/signer/sign_playbook.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: CLI to sign playbook bundle manifest

import argparse
import json
import base64
import tarfile
import shutil
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sign_bundle(bundle_path: Path, private_key_path: Path):
    """
    Sign playbook bundle manifest.
    
    Args:
        bundle_path: Path to playbook bundle
        private_key_path: Path to RSA private key
    """
    bundle_path = Path(bundle_path)
    private_key_path = Path(private_key_path)
    
    if not bundle_path.exists():
        raise FileNotFoundError(f"Bundle not found: {bundle_path}")
    
    if not private_key_path.exists():
        raise FileNotFoundError(f"Private key not found: {private_key_path}")
    
    # Load private key
    with open(private_key_path, 'rb') as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )
    
    # Extract bundle
    temp_dir = Path(f"/tmp/playbook_sign_{bundle_path.stem}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        with tarfile.open(bundle_path, 'r:gz') as tar:
            tar.extractall(temp_dir)
        
        # Load manifest
        manifest_path = temp_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError("manifest.json not found in bundle")
        
        with open(manifest_path, 'rb') as f:
            manifest_content = f.read()
        
        # Sign manifest
        signature = private_key.sign(
            manifest_content,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Save signature
        signature_path = temp_dir / "manifest.sig"
        with open(signature_path, 'wb') as f:
            f.write(base64.b64encode(signature))
        
        # Recreate bundle with signature
        logger.info(f"Signing bundle: {bundle_path}")
        with tarfile.open(bundle_path, 'w:gz') as tar:
            tar.add(temp_dir, arcname='.', recursive=True)
        
        logger.info("✓ Bundle signed successfully")
        
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

def main():
    parser = argparse.ArgumentParser(description='Sign playbook bundle')
    parser.add_argument('--bundle', type=str, required=True,
                       help='Path to playbook bundle')
    parser.add_argument('--key', type=str, required=True,
                       help='Path to RSA private key')
    
    args = parser.parse_args()
    
    try:
        sign_bundle(Path(args.bundle), Path(args.key))
        return 0
    except Exception as e:
        logger.error(f"Error signing bundle: {e}")
        return 1

if __name__ == "__main__":
    exit(main())

