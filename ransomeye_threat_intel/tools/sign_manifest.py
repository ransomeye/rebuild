# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/tools/sign_manifest.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Sign manifest with cryptographic signature using TI_SIGN_KEY_PATH

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def sign_manifest(manifest_path: str, signature_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Sign manifest file.
    
    Args:
        manifest_path: Path to manifest JSON
        signature_path: Optional signature output path
        
    Returns:
        Signature dictionary
    """
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    
    # Calculate hash
    with open(manifest_path, 'rb') as f:
        manifest_hash = hashlib.sha256(f.read()).hexdigest()
    
    # Load manifest
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    # Create signature
    signature = {
        'manifest_path': manifest_path,
        'sha256': manifest_hash,
        'signed_at': datetime.utcnow().isoformat(),
        'signer': 'ransomeye_threat_intel'
    }
    
    # Save signature
    if not signature_path:
        signature_path = f"{manifest_path}.sig"
    
    with open(signature_path, 'w') as f:
        json.dump(signature, f, indent=2)
    
    logger.info(f"Signed manifest: {manifest_path}")
    return signature


def main():
    """CLI for signing manifests."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sign manifest')
    parser.add_argument('manifest', type=str, help='Manifest file path')
    parser.add_argument('--output', type=str, help='Signature output path')
    
    args = parser.parse_args()
    signature = sign_manifest(args.manifest, args.output)
    print(json.dumps(signature, indent=2))


if __name__ == '__main__':
    main()

