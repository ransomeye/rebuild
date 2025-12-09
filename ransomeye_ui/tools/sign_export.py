#!/usr/bin/env python3
# Path and File Name : /home/ransomeye/rebuild/ransomeye_ui/tools/sign_export.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Dashboard export signing utility using UI_SIGN_KEY_PATH

import os
import sys
import json
import argparse
import base64
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend

def load_private_key(key_path: str):
    """Load RSA private key from file."""
    with open(key_path, 'rb') as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )
    return private_key

def sign_data(data: bytes, private_key) -> str:
    """Sign data with RSA private key."""
    signature = private_key.sign(
        data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode('utf-8')

def sign_manifest(manifest_path: str, key_path: str = None) -> str:
    """
    Sign a manifest file.
    
    Args:
        manifest_path: Path to manifest.json
        key_path: Path to private key (default: UI_SIGN_KEY_PATH env var)
    
    Returns:
        Path to signature file
    """
    manifest_path = Path(manifest_path)
    
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")
    
    # Get key path
    if key_path is None:
        key_path = os.environ.get('UI_SIGN_KEY_PATH', '')
    
    if not key_path or not os.path.exists(key_path):
        raise FileNotFoundError(
            f"Sign key not found. Set UI_SIGN_KEY_PATH environment variable or provide -k option."
        )
    
    # Load manifest
    with open(manifest_path, 'r') as f:
        manifest_data = json.load(f)
    
    # Load private key
    private_key = load_private_key(key_path)
    
    # Create canonical JSON (sorted keys)
    manifest_json = json.dumps(manifest_data, sort_keys=True).encode('utf-8')
    
    # Sign manifest
    signature = sign_data(manifest_json, private_key)
    
    # Create signature object
    signature_data = {
        "manifest_hash": manifest_data.get("hash", ""),
        "signature": signature,
        "algorithm": "RSA-PSS-SHA256",
        "key_id": os.path.basename(key_path)
    }
    
    # Write signature file
    signature_file = manifest_path.parent / "manifest.sig"
    with open(signature_file, 'w') as f:
        json.dump(signature_data, f, indent=2)
    
    return str(signature_file)

def main():
    parser = argparse.ArgumentParser(description='Sign RansomEye dashboard manifest')
    parser.add_argument('manifest', help='Path to manifest.json file')
    parser.add_argument('-k', '--key', help='Path to private key file', default=None)
    
    args = parser.parse_args()
    
    try:
        signature_file = sign_manifest(args.manifest, args.key)
        print(f"✓ Manifest signed successfully: {signature_file}")
        sys.exit(0)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()

