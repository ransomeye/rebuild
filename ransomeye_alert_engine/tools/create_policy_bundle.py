# Path and File Name : /home/ransomeye/rebuild/ransomeye_alert_engine/tools/create_policy_bundle.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: CLI tool to package YAML policy files into .tar.gz bundle with manifest.json

import argparse
import json
import hashlib
import tarfile
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def create_manifest(policy_dir: Path) -> dict:
    """
    Create manifest.json with SHA256 hashes of all files.
    
    Args:
        policy_dir: Directory containing policy files
        
    Returns:
        Manifest dictionary
    """
    manifest = {
        'files': {}
    }
    
    # Walk directory and hash all files
    for root, dirs, files in os.walk(policy_dir):
        root_path = Path(root)
        for filename in files:
            file_path = root_path / filename
            
            # Skip manifest.json itself (will be added later)
            if filename == 'manifest.json':
                continue
            
            # Calculate hash
            file_hash = calculate_sha256(file_path)
            rel_path = file_path.relative_to(policy_dir)
            manifest['files'][str(rel_path)] = file_hash
            logger.info(f"Hashed: {rel_path} -> {file_hash[:16]}...")
    
    return manifest

def create_bundle(policy_dir: Path, output_path: Path):
    """
    Create a policy bundle (.tar.gz) with manifest.json.
    
    Args:
        policy_dir: Directory containing policy YAML files
        output_path: Output bundle file path
    """
    policy_dir = Path(policy_dir)
    output_path = Path(output_path)
    
    if not policy_dir.exists():
        raise ValueError(f"Policy directory does not exist: {policy_dir}")
    
    # Create manifest
    logger.info("Creating manifest.json...")
    manifest = create_manifest(policy_dir)
    
    # Write manifest to policy directory
    manifest_path = policy_dir / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    # Add manifest to files list (hash it)
    manifest_hash = calculate_sha256(manifest_path)
    manifest['files']['manifest.json'] = manifest_hash
    
    # Update manifest with its own hash
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    # Create tar.gz bundle
    logger.info(f"Creating bundle: {output_path}")
    with tarfile.open(output_path, 'w:gz') as tar:
        tar.add(policy_dir, arcname='.', recursive=True)
    
    logger.info(f"Bundle created successfully: {output_path}")
    logger.info(f"Bundle SHA256: {calculate_sha256(output_path)}")

def main():
    parser = argparse.ArgumentParser(description='Create policy bundle with manifest')
    parser.add_argument('--policy-dir', type=str, required=True,
                       help='Directory containing policy YAML files')
    parser.add_argument('--output', type=str, required=True,
                       help='Output bundle file path (.tar.gz)')
    
    args = parser.parse_args()
    
    try:
        create_bundle(Path(args.policy_dir), Path(args.output))
        return 0
    except Exception as e:
        logger.error(f"Error creating bundle: {e}")
        return 1

if __name__ == "__main__":
    exit(main())

