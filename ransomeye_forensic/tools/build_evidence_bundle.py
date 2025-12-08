# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/tools/build_evidence_bundle.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: CLI tool to package forensic artifacts and ledger for export

import argparse
import json
import tarfile
import hashlib
import shutil
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

def build_evidence_bundle(artifact_ids: list, ledger_path: Path, output_path: Path, storage_dir: Path):
    """
    Build evidence bundle containing artifacts and ledger.
    
    Args:
        artifact_ids: List of artifact IDs to include
        ledger_path: Path to evidence ledger
        output_path: Output bundle file path
        storage_dir: Artifact storage directory
    """
    output_path = Path(output_path)
    storage_dir = Path(storage_dir)
    
    # Create temporary directory for bundle contents
    temp_dir = Path(f"/tmp/evidence_bundle_{output_path.stem}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Copy ledger
        if ledger_path.exists():
            shutil.copy2(ledger_path, temp_dir / "evidence_ledger.jsonl")
            logger.info(f"Added ledger to bundle")
        
        # Copy artifacts
        artifacts_dir = temp_dir / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)
        
        manifest = {
            'artifacts': [],
            'files': {}
        }
        
        for artifact_id in artifact_ids:
            artifact_storage = storage_dir / artifact_id
            if artifact_storage.exists():
                # Copy artifact directory
                artifact_bundle_dir = artifacts_dir / artifact_id
                shutil.copytree(artifact_storage, artifact_bundle_dir)
                
                # Calculate hash
                artifact_hash = calculate_sha256(artifact_storage / "chunk_000000.zst") if (artifact_storage / "chunk_000000.zst").exists() else "unknown"
                
                manifest['artifacts'].append({
                    'artifact_id': artifact_id,
                    'hash': artifact_hash
                })
                
                logger.info(f"Added artifact {artifact_id} to bundle")
        
        # Create manifest
        manifest_path = temp_dir / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Hash all files
        for root, dirs, files in os.walk(temp_dir):
            for filename in files:
                file_path = Path(root) / filename
                rel_path = file_path.relative_to(temp_dir)
                file_hash = calculate_sha256(file_path)
                manifest['files'][str(rel_path)] = file_hash
        
        # Update manifest with file hashes
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Create tar.gz bundle
        logger.info(f"Creating evidence bundle: {output_path}")
        with tarfile.open(output_path, 'w:gz') as tar:
            tar.add(temp_dir, arcname='.', recursive=True)
        
        logger.info(f"Evidence bundle created: {output_path}")
        
    finally:
        # Clean up temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

def main():
    parser = argparse.ArgumentParser(description='Build evidence bundle')
    parser.add_argument('--artifacts', type=str, nargs='+', required=True,
                       help='Artifact IDs to include')
    parser.add_argument('--ledger', type=str, required=True,
                       help='Path to evidence ledger')
    parser.add_argument('--storage', type=str, required=True,
                       help='Artifact storage directory')
    parser.add_argument('--output', type=str, required=True,
                       help='Output bundle file path (.tar.gz)')
    
    args = parser.parse_args()
    
    try:
        build_evidence_bundle(
            args.artifacts,
            Path(args.ledger),
            Path(args.output),
            Path(args.storage)
        )
        return 0
    except Exception as e:
        logger.error(f"Error building evidence bundle: {e}")
        return 1

if __name__ == "__main__":
    import shutil
    import os
    exit(main())

