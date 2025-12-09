# Path and File Name : /home/ransomeye/rebuild/ransomeye_dpi_probe/tools/build_update_bundle.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Helper script for CI to build update bundles

import os
import sys
import json
import hashlib
import tarfile
import logging
from pathlib import Path
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def sign_bundle(bundle_path: Path, private_key_path: Path) -> str:
    """Sign bundle with private key."""
    # Load private key
    with open(private_key_path, 'rb') as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )
    
    # Calculate hash
    bundle_hash = calculate_sha256(bundle_path)
    message = bundle_hash.encode('utf-8')
    
    # Sign
    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    
    return signature.hex()


def build_update_bundle(source_dir: Path, output_dir: Path, version: str,
                       private_key_path: Path = None) -> Path:
    """
    Build update bundle tar.gz file.
    
    Args:
        source_dir: Source directory containing probe files
        output_dir: Output directory for bundle
        version: Version string
        private_key_path: Optional path to private key for signing
        
    Returns:
        Path to created bundle file
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    bundle_filename = f"ransomeye-probe-{version}-{timestamp}.tar.gz"
    bundle_path = output_dir / bundle_filename
    
    logger.info(f"Building update bundle: {bundle_path}")
    
    # Create tar.gz
    with tarfile.open(bundle_path, 'w:gz') as tar:
        # Add all files from source directory
        for root, dirs, files in os.walk(source_dir):
            # Skip hidden directories and __pycache__
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if file.startswith('.') or file.endswith('.pyc'):
                    continue
                
                file_path = Path(root) / file
                arcname = file_path.relative_to(source_dir)
                tar.add(file_path, arcname=arcname)
                logger.debug(f"Added: {arcname}")
    
    logger.info(f"Bundle created: {bundle_path} ({bundle_path.stat().st_size / 1024 / 1024:.2f} MB)")
    
    # Calculate hash
    bundle_hash = calculate_sha256(bundle_path)
    logger.info(f"Bundle SHA256: {bundle_hash}")
    
    # Create manifest
    manifest = {
        'version': version,
        'timestamp': timestamp,
        'filename': bundle_filename,
        'sha256': bundle_hash,
        'size': bundle_path.stat().st_size,
        'created_at': datetime.now().isoformat()
    }
    
    # Sign if key provided
    if private_key_path and private_key_path.exists():
        try:
            signature = sign_bundle(bundle_path, private_key_path)
            manifest['signature'] = signature
            logger.info("Bundle signed")
        except Exception as e:
            logger.error(f"Error signing bundle: {e}")
    
    # Save manifest
    manifest_path = output_dir / f"{Path(bundle_filename).stem}.manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    logger.info(f"Manifest saved: {manifest_path}")
    
    return bundle_path


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Build update bundle for DPI Probe')
    parser.add_argument('--source', type=str, required=True, help='Source directory')
    parser.add_argument('--output', type=str, required=True, help='Output directory')
    parser.add_argument('--version', type=str, required=True, help='Version string')
    parser.add_argument('--sign-key', type=str, help='Private key path for signing')
    
    args = parser.parse_args()
    
    source_dir = Path(args.source)
    if not source_dir.exists():
        logger.error(f"Source directory not found: {source_dir}")
        sys.exit(1)
    
    output_dir = Path(args.output)
    private_key_path = Path(args.sign_key) if args.sign_key else None
    
    bundle_path = build_update_bundle(source_dir, output_dir, args.version, private_key_path)
    
    logger.info(f"Update bundle built successfully: {bundle_path}")


if __name__ == '__main__':
    main()

