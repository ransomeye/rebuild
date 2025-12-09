# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/tools/verify_manifest.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Verify manifest signature

import os
import json
import hashlib
from typing import Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verify_manifest(manifest_path: str, signature_path: Optional[str] = None) -> Dict[str, Any]:
    """Verify manifest signature."""
    if not os.path.exists(manifest_path):
        return {'valid': False, 'error': 'Manifest not found'}
    
    if not signature_path:
        signature_path = f"{manifest_path}.sig"
    
    if not os.path.exists(signature_path):
        return {'valid': False, 'error': 'Signature not found'}
    
    # Calculate current hash
    with open(manifest_path, 'rb') as f:
        current_hash = hashlib.sha256(f.read()).hexdigest()
    
    # Load signature
    with open(signature_path, 'r') as f:
        signature = json.load(f)
    
    expected_hash = signature.get('sha256', '')
    valid = current_hash == expected_hash
    
    return {
        'valid': valid,
        'expected_hash': expected_hash,
        'current_hash': current_hash
    }


def main():
    """CLI for verifying manifests."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify manifest signature')
    parser.add_argument('manifest', type=str, help='Manifest file')
    parser.add_argument('--signature', type=str, help='Signature file')
    
    args = parser.parse_args()
    result = verify_manifest(args.manifest, args.signature)
    print(json.dumps(result, indent=2))
    
    if not result['valid']:
        exit(1)


if __name__ == '__main__':
    main()

