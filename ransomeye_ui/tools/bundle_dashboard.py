#!/usr/bin/env python3
# Path and File Name : /home/ransomeye/rebuild/ransomeye_ui/tools/bundle_dashboard.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Python script to export dashboard JSON with manifest signature

import os
import sys
import json
import hashlib
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def calculate_hash(data: bytes) -> str:
    """Calculate SHA256 hash of data."""
    return hashlib.sha256(data).hexdigest()

def create_manifest(dashboard_data: dict, dashboard_hash: str) -> dict:
    """Create manifest for dashboard bundle."""
    return {
        "dashboard_id": dashboard_data.get("id", "unknown"),
        "dashboard_name": dashboard_data.get("name", "Unknown"),
        "schema_version": dashboard_data.get("schema_version", "1.0.0"),
        "hash": dashboard_hash,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "exported_by": os.environ.get("USER", "system"),
        "version": "1.0.0"
    }

def bundle_dashboard(dashboard_path: str, output_dir: str = None, sign: bool = False) -> str:
    """
    Bundle dashboard JSON with manifest.
    
    Args:
        dashboard_path: Path to dashboard JSON file
        output_dir: Output directory (default: same as dashboard)
        sign: Whether to sign the bundle
    
    Returns:
        Path to created bundle directory
    """
    dashboard_path = Path(dashboard_path)
    
    if not dashboard_path.exists():
        raise FileNotFoundError(f"Dashboard file not found: {dashboard_path}")
    
    # Load dashboard
    with open(dashboard_path, 'r') as f:
        dashboard_data = json.load(f)
    
    # Calculate hash
    dashboard_json = json.dumps(dashboard_data, sort_keys=True).encode('utf-8')
    dashboard_hash = calculate_hash(dashboard_json)
    
    # Create manifest
    manifest = create_manifest(dashboard_data, dashboard_hash)
    
    # Determine output directory
    if output_dir is None:
        output_dir = dashboard_path.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create bundle directory
    dashboard_id = dashboard_data.get("id", "dashboard")
    bundle_dir = output_dir / f"{dashboard_id}_bundle"
    bundle_dir.mkdir(exist_ok=True)
    
    # Write dashboard JSON
    dashboard_file = bundle_dir / "dashboard.json"
    with open(dashboard_file, 'w') as f:
        json.dump(dashboard_data, f, indent=2)
    
    # Write manifest
    manifest_file = bundle_dir / "manifest.json"
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    # Sign if requested
    if sign:
        sign_key_path = os.environ.get('UI_SIGN_KEY_PATH', '')
        if sign_key_path and os.path.exists(sign_key_path):
            # Import signing utility
            sign_script = Path(__file__).parent / "sign_export.py"
            if sign_script.exists():
                import subprocess
                result = subprocess.run(
                    [sys.executable, str(sign_script), str(manifest_file)],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print(f"✓ Dashboard signed successfully")
                else:
                    print(f"⚠ Signing failed: {result.stderr}")
            else:
                print("⚠ Sign script not found, skipping signature")
        else:
            print("⚠ Sign key not configured, skipping signature")
    
    print(f"✓ Dashboard bundled: {bundle_dir}")
    print(f"  - Dashboard: {dashboard_file}")
    print(f"  - Manifest: {manifest_file}")
    print(f"  - Hash: {dashboard_hash}")
    
    return str(bundle_dir)

def main():
    parser = argparse.ArgumentParser(description='Bundle RansomEye dashboard with manifest')
    parser.add_argument('dashboard', help='Path to dashboard JSON file')
    parser.add_argument('-o', '--output', help='Output directory', default=None)
    parser.add_argument('-s', '--sign', action='store_true', help='Sign the bundle')
    
    args = parser.parse_args()
    
    try:
        bundle_path = bundle_dashboard(args.dashboard, args.output, args.sign)
        print(f"\n✓ Bundle created successfully: {bundle_path}")
        sys.exit(0)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()

