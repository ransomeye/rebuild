# Path and File Name : /home/ransomeye/rebuild/ransomeye_response/tools/create_playbook_bundle.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: CLI to zip YAML playbook and manifest into bundle

import argparse
import json
import tarfile
import hashlib
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def create_bundle(playbook_yaml: Path, output_path: Path, metadata: dict = None):
    """
    Create playbook bundle.
    
    Args:
        playbook_yaml: Path to playbook YAML file
        output_path: Output bundle path
        metadata: Optional metadata dictionary
    """
    playbook_yaml = Path(playbook_yaml)
    output_path = Path(output_path)
    
    if not playbook_yaml.exists():
        raise FileNotFoundError(f"Playbook YAML not found: {playbook_yaml}")
    
    # Create manifest
    manifest = {
        'name': metadata.get('name', playbook_yaml.stem) if metadata else playbook_yaml.stem,
        'version': metadata.get('version', '1.0.0') if metadata else '1.0.0',
        'risk_level': metadata.get('risk_level', 'medium') if metadata else 'medium',
        'created_at': datetime.utcnow().isoformat() + 'Z',
        'playbook_file': playbook_yaml.name
    }
    
    if metadata:
        manifest.update(metadata)
    
    # Calculate playbook hash
    playbook_hash = calculate_file_hash(playbook_yaml)
    manifest['playbook_hash'] = playbook_hash
    
    # Create temporary directory for bundle contents
    temp_dir = Path(f"/tmp/playbook_bundle_{output_path.stem}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Copy playbook YAML
        shutil.copy2(playbook_yaml, temp_dir / playbook_yaml.name)
        
        # Save manifest
        manifest_path = temp_dir / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Create tar.gz bundle
        logger.info(f"Creating bundle: {output_path}")
        with tarfile.open(output_path, 'w:gz') as tar:
            tar.add(temp_dir, arcname='.', recursive=True)
        
        logger.info(f"Bundle created: {output_path}")
        logger.info(f"Manifest hash: {calculate_file_hash(manifest_path)}")
        
    finally:
        # Cleanup
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

def main():
    parser = argparse.ArgumentParser(description='Create playbook bundle')
    parser.add_argument('--playbook', type=str, required=True,
                       help='Path to playbook YAML file')
    parser.add_argument('--output', type=str, required=True,
                       help='Output bundle path (.tar.gz)')
    parser.add_argument('--name', type=str, help='Playbook name')
    parser.add_argument('--version', type=str, help='Playbook version')
    parser.add_argument('--risk-level', type=str, choices=['low', 'medium', 'high', 'critical'],
                       help='Risk level')
    
    args = parser.parse_args()
    
    metadata = {}
    if args.name:
        metadata['name'] = args.name
    if args.version:
        metadata['version'] = args.version
    if args.risk_level:
        metadata['risk_level'] = args.risk_level
    
    try:
        create_bundle(Path(args.playbook), Path(args.output), metadata)
        return 0
    except Exception as e:
        logger.error(f"Error creating bundle: {e}")
        return 1

if __name__ == "__main__":
    import shutil
    exit(main())

