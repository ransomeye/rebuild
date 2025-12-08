# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_core/tools/create_model_bundle.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: CLI tool to create model bundles with manifest.json containing SHA256 hashes

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

def create_manifest(model_dir: Path, metadata: dict) -> dict:
    """
    Create manifest.json with SHA256 hashes of all files.
    
    Args:
        model_dir: Directory containing model files
        metadata: Model metadata dictionary
        
    Returns:
        Manifest dictionary
    """
    manifest = {
        'metadata': metadata,
        'files': {}
    }
    
    # Walk directory and hash all files
    for root, dirs, files in os.walk(model_dir):
        root_path = Path(root)
        for filename in files:
            file_path = root_path / filename
            rel_path = file_path.relative_to(model_dir)
            
            # Skip manifest.json itself (will be added later)
            if rel_path.name == 'manifest.json':
                continue
            
            # Calculate hash
            file_hash = calculate_sha256(file_path)
            manifest['files'][str(rel_path)] = file_hash
            logger.info(f"Hashed: {rel_path} -> {file_hash[:16]}...")
    
    return manifest

def create_bundle(model_dir: Path, output_path: Path, metadata_path: Path = None):
    """
    Create a model bundle (.tar.gz) with manifest.json.
    
    Args:
        model_dir: Directory containing model files
        output_path: Output bundle file path
        metadata_path: Optional path to metadata.json file
    """
    model_dir = Path(model_dir)
    output_path = Path(output_path)
    
    if not model_dir.exists():
        raise ValueError(f"Model directory does not exist: {model_dir}")
    
    # Load metadata
    if metadata_path:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    else:
        metadata_file = model_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        else:
            raise ValueError("metadata.json not found in model directory and not provided")
    
    # Create manifest
    logger.info("Creating manifest.json...")
    manifest = create_manifest(model_dir, metadata)
    
    # Write manifest to model directory
    manifest_path = model_dir / "manifest.json"
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
        tar.add(model_dir, arcname='.', recursive=True)
    
    logger.info(f"Bundle created successfully: {output_path}")
    logger.info(f"Bundle SHA256: {calculate_sha256(output_path)}")

def main():
    parser = argparse.ArgumentParser(description='Create model bundle with manifest')
    parser.add_argument('--model-dir', type=str, required=True,
                       help='Directory containing model files')
    parser.add_argument('--output', type=str, required=True,
                       help='Output bundle file path (.tar.gz)')
    parser.add_argument('--metadata', type=str, default=None,
                       help='Path to metadata.json file (optional if in model-dir)')
    
    args = parser.parse_args()
    
    try:
        create_bundle(
            Path(args.model_dir),
            Path(args.output),
            Path(args.metadata) if args.metadata else None
        )
        return 0
    except Exception as e:
        logger.error(f"Error creating bundle: {e}")
        return 1

if __name__ == "__main__":
    exit(main())

