# Path and File Name : /home/ransomeye/rebuild/ransomeye_install/tools/verify_manifest.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Verify RSA signature of version manifest for integrity validation

import argparse
import json
import os
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

def load_public_key(key_path):
    """Load RSA public key from file."""
    with open(key_path, 'rb') as f:
        public_key = serialization.load_pem_public_key(
            f.read(),
            backend=default_backend()
        )
    return public_key

def verify_manifest(manifest_path, public_key_path):
    """Verify manifest signature with RSA public key."""
    # Load manifest
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    if 'signature' not in manifest:
        print("Error: Manifest does not contain a signature")
        return False
    
    # Extract signature
    signature_b64 = manifest.pop('signature')
    signed_at = manifest.pop('signed_at', None)
    
    # Load public key
    if not os.path.exists(public_key_path):
        print(f"Error: Public key file does not exist: {public_key_path}")
        return False
    
    public_key = load_public_key(public_key_path)
    
    # Recreate manifest content (without signature)
    manifest_json = json.dumps(manifest, sort_keys=True, separators=(',', ':'))
    manifest_bytes = manifest_json.encode('utf-8')
    
    # Decode signature
    signature = base64.b64decode(signature_b64)
    
    # Verify
    try:
        public_key.verify(
            signature,
            manifest_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        print("✓ Manifest signature is valid")
        if signed_at:
            print(f"  Signed at: {signed_at}")
        return True
    except InvalidSignature:
        print("✗ Manifest signature is invalid")
        return False
    except Exception as e:
        print(f"✗ Error verifying signature: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Verify version manifest signature')
    parser.add_argument('--manifest', type=str, required=True, help='Signed manifest JSON file')
    parser.add_argument('--key', type=str, required=True, help='RSA public key file path')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.manifest):
        print(f"Error: Manifest file does not exist: {args.manifest}")
        return 1
    
    try:
        if verify_manifest(args.manifest, args.key):
            return 0
        else:
            return 1
    except Exception as e:
        print(f"Error verifying manifest: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())

