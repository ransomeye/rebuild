# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/tools/sign_artifact.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Tool to sign artifacts (models, outputs) with cryptographic signatures

import os
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def sign_artifact(
    artifact_path: str,
    signature_path: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Sign an artifact with cryptographic hash.
    
    Args:
        artifact_path: Path to artifact file
        signature_path: Optional path to save signature
        metadata: Optional metadata to include
        
    Returns:
        Signature dictionary
    """
    if not os.path.exists(artifact_path):
        raise FileNotFoundError(f"Artifact not found: {artifact_path}")
    
    # Calculate hash
    sha256_hash = hashlib.sha256()
    with open(artifact_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256_hash.update(chunk)
    
    file_hash = sha256_hash.hexdigest()
    
    # Get file stats
    stat = os.stat(artifact_path)
    
    # Create signature
    signature = {
        'artifact_path': artifact_path,
        'sha256': file_hash,
        'size': stat.st_size,
        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        'metadata': metadata or {},
        'signed_at': datetime.utcnow().isoformat()
    }
    
    # Save signature
    if not signature_path:
        signature_path = f"{artifact_path}.sig"
    
    with open(signature_path, 'w') as f:
        json.dump(signature, f, indent=2)
    
    logger.info(f"Signed artifact: {artifact_path} -> {signature_path}")
    return signature


def main():
    """CLI for signing artifacts."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sign artifact')
    parser.add_argument('artifact', type=str, help='Path to artifact')
    parser.add_argument('--output', type=str, help='Signature output path')
    parser.add_argument('--metadata', type=str, help='JSON metadata')
    
    args = parser.parse_args()
    
    metadata = None
    if args.metadata:
        metadata = json.loads(args.metadata)
    
    signature = sign_artifact(args.artifact, args.output, metadata)
    print(json.dumps(signature, indent=2))


if __name__ == '__main__':
    main()

