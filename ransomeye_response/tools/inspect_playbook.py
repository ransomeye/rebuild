# Path and File Name : /home/ransomeye/rebuild/ransomeye_response/tools/inspect_playbook.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: CLI to view details of a playbook bundle

import argparse
import json
import tarfile
import yaml
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def inspect_bundle(bundle_path: Path):
    """
    Inspect playbook bundle and display details.
    
    Args:
        bundle_path: Path to playbook bundle
    """
    bundle_path = Path(bundle_path)
    
    if not bundle_path.exists():
        raise FileNotFoundError(f"Bundle not found: {bundle_path}")
    
    # Extract to temp directory
    temp_dir = Path(f"/tmp/playbook_inspect_{bundle_path.stem}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        with tarfile.open(bundle_path, 'r:gz') as tar:
            tar.extractall(temp_dir)
        
        # Load manifest
        manifest_path = temp_dir / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            print("=== Playbook Manifest ===")
            print(json.dumps(manifest, indent=2))
            print()
        
        # Load playbook YAML
        playbook_yaml = None
        for yaml_file in temp_dir.glob("*.yaml"):
            playbook_yaml = yaml_file
            break
        for yaml_file in temp_dir.glob("*.yml"):
            playbook_yaml = yaml_file
            break
        
        if playbook_yaml:
            with open(playbook_yaml, 'r') as f:
                playbook_data = yaml.safe_load(f)
            
            print("=== Playbook Content ===")
            print(f"Name: {playbook_data.get('name', 'unknown')}")
            print(f"Version: {playbook_data.get('version', 'unknown')}")
            print(f"Risk Level: {playbook_data.get('risk_level', 'unknown')}")
            print(f"Steps: {len(playbook_data.get('steps', []))}")
            print()
            
            print("=== Steps ===")
            for i, step in enumerate(playbook_data.get('steps', []), 1):
                print(f"{i}. {step.get('id')} - {step.get('name')}")
                print(f"   Action: {step.get('action')}")
                print(f"   Target: {step.get('target', {})}")
                if 'rollback' in step:
                    print(f"   Rollback: {step['rollback'].get('action')}")
                print()
        
        # Check for signature
        sig_path = temp_dir / "manifest.sig"
        if sig_path.exists():
            print("=== Signature ===")
            print("✓ manifest.sig found")
        else:
            print("=== Signature ===")
            print("✗ manifest.sig not found (bundle not signed)")
        
    finally:
        # Cleanup
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

def main():
    parser = argparse.ArgumentParser(description='Inspect playbook bundle')
    parser.add_argument('--bundle', type=str, required=True,
                       help='Path to playbook bundle')
    
    args = parser.parse_args()
    
    try:
        inspect_bundle(Path(args.bundle))
        return 0
    except Exception as e:
        logger.error(f"Error inspecting bundle: {e}")
        return 1

if __name__ == "__main__":
    import shutil
    exit(main())

