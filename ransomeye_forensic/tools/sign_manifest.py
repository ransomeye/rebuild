# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/tools/sign_manifest.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: CLI tool to sign evidence manifest using RSA private key

import argparse
import json
import base64
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_private_key(key_path: Path):
    """Load RSA private key from file."""
    with open(key_path, 'rb') as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )
    return private_key

def sign_manifest(manifest_path: Path, private_key_path: Path, output_path: Path = None):
    """
    Sign manifest.json with RSA private key.
    
    Args:
        manifest_path: Path to manifest.json
        private_key_path: Path to RSA private key
        output_path: Optional output path for signature
    """
    manifest_path = Path(manifest_path)
    private_key_path = Path(private_key_path)
    
    if not manifest_path.exists():
        raise ValueError(f"Manifest file not found: {manifest_path}")
    
    private_key = load_private_key(private_key_path)
    
    # Read manifest content
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
    
    # Encode signature
    signature_b64 = base64.b64encode(signature).decode('utf-8')
    
    # Write signature file
    if output_path is None:
        output_path = manifest_path.parent / "manifest.sig"
    else:
        output_path = Path(output_path)
    
    with open(output_path, 'w') as f:
        f.write(signature_b64)
    
    logger.info(f"Manifest signed successfully: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Sign evidence manifest')
    parser.add_argument('--manifest', type=str, required=True,
                       help='Path to manifest.json')
    parser.add_argument('--key', type=str, required=True,
                       help='Path to RSA private key file')
    parser.add_argument('--output', type=str, default=None,
                       help='Output signature file path')
    
    args = parser.parse_args()
    
    try:
        sign_manifest(
            Path(args.manifest),
            Path(args.key),
            Path(args.output) if args.output else None
        )
        return 0
    except Exception as e:
        logger.error(f"Error signing manifest: {e}")
        return 1

if __name__ == "__main__":
    exit(main())

