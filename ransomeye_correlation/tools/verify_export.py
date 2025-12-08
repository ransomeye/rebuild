# Path and File Name : /home/ransomeye/rebuild/ransomeye_correlation/tools/verify_export.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: CLI to verify export bundle signature

import argparse
import sys
import tarfile
import json
import base64
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_export(bundle_path: Path, public_key_path: Path):
    """
    Verify export bundle signature.
    
    Args:
        bundle_path: Path to signed bundle
        public_key_path: Path to public key
    """
    # Extract bundle
    temp_dir = Path(f"/tmp/verify_export_{bundle_path.stem}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        with tarfile.open(bundle_path, 'r:gz') as tar:
            tar.extractall(temp_dir)
        
        # Load public key
        with open(public_key_path, 'rb') as f:
            public_key = serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )
        
        # Load manifest and signature
        manifest_file = temp_dir / "manifest.json"
        signature_file = temp_dir / "manifest.sig"
        
        if not manifest_file.exists():
            logger.error("manifest.json not found")
            return False
        
        if not signature_file.exists():
            logger.error("manifest.sig not found")
            return False
        
        # Read manifest
        with open(manifest_file, 'rb') as f:
            manifest_content = f.read()
        
        # Read signature
        with open(signature_file, 'rb') as f:
            signature = base64.b64decode(f.read())
        
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
            logger.info("✓ Export signature verified")
            return True
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False
            
    finally:
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

def main():
    parser = argparse.ArgumentParser(description='Verify export bundle signature')
    parser.add_argument('--bundle', type=str, required=True,
                       help='Signed bundle path')
    parser.add_argument('--public-key', type=str, required=True,
                       help='Public key path')
    
    args = parser.parse_args()
    
    try:
        bundle_path = Path(args.bundle)
        public_key_path = Path(args.public_key)
        
        if not bundle_path.exists():
            logger.error(f"Bundle not found: {bundle_path}")
            return 1
        
        if not public_key_path.exists():
            logger.error(f"Public key not found: {public_key_path}")
            return 1
        
        success = verify_export(bundle_path, public_key_path)
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Error verifying export: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main())

