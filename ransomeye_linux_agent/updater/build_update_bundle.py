# Path and File Name : /home/ransomeye/rebuild/ransomeye_linux_agent/updater/build_update_bundle.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Tool to package agent updates with signature

import os
import sys
import tarfile
import hashlib
from pathlib import Path
from datetime import datetime
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def build_bundle(source_dir: str, output_path: str, private_key_path: str):
    """
    Build signed update bundle.
    
    Args:
        source_dir: Source directory containing agent files
        output_path: Output bundle path
        private_key_path: Path to private key for signing
    """
    source_path = Path(source_dir)
    output_file = Path(output_path)
    
    if not source_path.exists():
        print(f"Error: Source directory not found: {source_dir}")
        sys.exit(1)
    
    # Create tar.gz bundle
    print(f"Creating bundle: {output_file}")
    with tarfile.open(output_file, 'w:gz') as tar:
        tar.add(source_path, arcname='ransomeye-agent')
    
    print(f"Bundle created: {output_file}")
    
    # Sign bundle
    if Path(private_key_path).exists():
        print(f"Signing bundle with key: {private_key_path}")
        sign_bundle(output_file, private_key_path)
    else:
        print(f"Warning: Private key not found: {private_key_path}")
        print("Bundle created but not signed")


def sign_bundle(bundle_path: Path, private_key_path: str):
    """
    Sign bundle with RSA private key.
    
    Args:
        bundle_path: Path to bundle file
        private_key_path: Path to private key
    """
    # Load private key
    with open(private_key_path, 'rb') as f:
        private_key = RSA.import_key(f.read())
    
    # Read bundle
    with open(bundle_path, 'rb') as f:
        bundle_content = f.read()
    
    # Create hash
    bundle_hash = SHA256.new(bundle_content)
    
    # Sign
    signature = pkcs1_15.new(private_key).sign(bundle_hash)
    
    # Save signature
    sig_path = bundle_path.with_suffix(bundle_path.suffix + '.sig')
    with open(sig_path, 'wb') as f:
        f.write(signature)
    
    print(f"Signature saved: {sig_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python build_update_bundle.py <source_dir> <output.tar.gz> [private_key.pem]")
        sys.exit(1)
    
    source_dir = sys.argv[1]
    output_path = sys.argv[2]
    private_key_path = sys.argv[3] if len(sys.argv) > 3 else os.environ.get(
        'AGENT_UPDATE_KEY_PATH',
        '/etc/ransomeye-agent/keys/update_key.pem'
    )
    
    build_bundle(source_dir, output_path, private_key_path)

