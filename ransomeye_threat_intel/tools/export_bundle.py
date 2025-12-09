# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/tools/export_bundle.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Export IOC bundle as signed tarball

import os
import json
import tarfile
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def export_bundle(
    iocs: List[Dict[str, Any]],
    output_path: str,
    sign: bool = True
) -> Dict[str, Any]:
    """
    Export IOCs as signed bundle.
    
    Args:
        iocs: List of IOC dictionaries
        output_path: Output tarball path
        sign: Whether to sign the bundle
        
    Returns:
        Export metadata
    """
    # Create bundle directory
    bundle_dir = Path(output_path).parent / f"bundle_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    bundle_dir.mkdir(exist_ok=True)
    
    # Save IOCs
    iocs_file = bundle_dir / 'iocs.json'
    with open(iocs_file, 'w') as f:
        json.dump(iocs, f, indent=2)
    
    # Create manifest
    manifest = {
        'version': '1.0',
        'exported_at': datetime.utcnow().isoformat(),
        'ioc_count': len(iocs),
        'bundle_hash': hashlib.sha256(json.dumps(iocs, sort_keys=True).encode()).hexdigest()
    }
    
    manifest_file = bundle_dir / 'manifest.json'
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    # Sign manifest if requested
    if sign:
        from .sign_manifest import sign_manifest
        sign_manifest(str(manifest_file), str(bundle_dir / 'manifest.json.sig'))
    
    # Create tarball
    with tarfile.open(output_path, 'w:gz') as tar:
        tar.add(bundle_dir, arcname='bundle')
    
    logger.info(f"Exported bundle: {output_path}")
    
    return {
        'output_path': output_path,
        'ioc_count': len(iocs),
        'bundle_hash': manifest['bundle_hash'],
        'signed': sign
    }


def main():
    """CLI for exporting bundles."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Export IOC bundle')
    parser.add_argument('--iocs-file', type=str, help='JSON file with IOCs')
    parser.add_argument('--output', type=str, required=True, help='Output tarball path')
    parser.add_argument('--no-sign', action='store_true', help='Skip signing')
    
    args = parser.parse_args()
    
    if args.iocs_file:
        with open(args.iocs_file, 'r') as f:
            iocs = json.load(f)
    else:
        iocs = []
    
    result = export_bundle(iocs, args.output, sign=not args.no_sign)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

