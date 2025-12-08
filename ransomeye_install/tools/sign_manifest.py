# Path and File Name : /home/ransomeye/rebuild/ransomeye_install/tools/sign_manifest.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Sign version manifest using RSA private key for integrity verification

import argparse
import json
import os
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

def generate_key_pair(key_size=2048):
    """Generate RSA key pair."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend()
    )
    return private_key, private_key.public_key()

def load_private_key(key_path):
    """Load RSA private key from file."""
    with open(key_path, 'rb') as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )
    return private_key

def save_private_key(private_key, key_path):
    """Save RSA private key to file."""
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    os.makedirs(os.path.dirname(key_path), exist_ok=True)
    with open(key_path, 'wb') as f:
        f.write(pem)
    os.chmod(key_path, 0o600)

def save_public_key(public_key, key_path):
    """Save RSA public key to file."""
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    os.makedirs(os.path.dirname(key_path), exist_ok=True)
    with open(key_path, 'wb') as f:
        f.write(pem)

def sign_manifest(manifest_path, private_key_path, output_path=None):
    """Sign manifest with RSA private key."""
    # Load manifest
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    # Load private key
    if os.path.exists(private_key_path):
        private_key = load_private_key(private_key_path)
    else:
        print(f"Private key not found at {private_key_path}, generating new key pair...")
        private_key, public_key = generate_key_pair()
        save_private_key(private_key, private_key_path)
        public_key_path = private_key_path.replace('_private.pem', '_public.pem')
        save_public_key(public_key, public_key_path)
        print(f"Generated new key pair:")
        print(f"  Private key: {private_key_path}")
        print(f"  Public key: {public_key_path}")
    
    # Create signature of manifest content
    manifest_json = json.dumps(manifest, sort_keys=True, separators=(',', ':'))
    manifest_bytes = manifest_json.encode('utf-8')
    
    # Sign
    signature = private_key.sign(
        manifest_bytes,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    
    # Encode signature
    signature_b64 = base64.b64encode(signature).decode('utf-8')
    
    # Add signature to manifest
    manifest['signature'] = signature_b64
    manifest['signed_at'] = manifest.get('timestamp', '')
    
    # Save signed manifest
    output = output_path or manifest_path
    with open(output, 'w') as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    
    print(f"Manifest signed and saved to: {output}")
    return manifest

def main():
    parser = argparse.ArgumentParser(description='Sign version manifest with RSA key')
    parser.add_argument('--manifest', type=str, required=True, help='Manifest JSON file to sign')
    parser.add_argument('--key', type=str, required=True, help='RSA private key file path')
    parser.add_argument('--output', type=str, help='Output signed manifest path (default: overwrite input)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.manifest):
        print(f"Error: Manifest file does not exist: {args.manifest}")
        return 1
    
    try:
        sign_manifest(args.manifest, args.key, args.output)
        return 0
    except Exception as e:
        print(f"Error signing manifest: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())

