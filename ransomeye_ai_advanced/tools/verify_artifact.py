# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/tools/verify_artifact.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Tool to verify artifact signatures

import os
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verify_artifact(
    artifact_path: str,
    signature_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Verify artifact signature.
    
    Args:
        artifact_path: Path to artifact file
        signature_path: Optional path to signature file
        
    Returns:
        Verification result
    """
    if not os.path.exists(artifact_path):
        return {
            'valid': False,
            'error': 'Artifact not found'
        }
    
    # Find signature file
    if not signature_path:
        signature_path = f"{artifact_path}.sig"
    
    if not os.path.exists(signature_path):
        return {
            'valid': False,
            'error': 'Signature file not found'
        }
    
    # Load signature
    try:
        with open(signature_path, 'r') as f:
            signature = json.load(f)
    except Exception as e:
        return {
            'valid': False,
            'error': f'Error loading signature: {e}'
        }
    
    # Calculate current hash
    sha256_hash = hashlib.sha256()
    with open(artifact_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256_hash.update(chunk)
    
    current_hash = sha256_hash.hexdigest()
    expected_hash = signature.get('sha256', '')
    
    # Verify
    valid = current_hash == expected_hash
    
    result = {
        'valid': valid,
        'artifact_path': artifact_path,
        'expected_hash': expected_hash,
        'current_hash': current_hash,
        'signature_metadata': signature.get('metadata', {})
    }
    
    if not valid:
        result['error'] = 'Hash mismatch - artifact may have been modified'
    
    return result


def main():
    """CLI for verifying artifacts."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify artifact signature')
    parser.add_argument('artifact', type=str, help='Path to artifact')
    parser.add_argument('--signature', type=str, help='Signature file path')
    
    args = parser.parse_args()
    
    result = verify_artifact(args.artifact, args.signature)
    print(json.dumps(result, indent=2))
    
    if not result['valid']:
        exit(1)


if __name__ == '__main__':
    main()

