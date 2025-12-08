# Path and File Name : /home/ransomeye/rebuild/ransomeye_correlation/tools/sign_export.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: CLI to sign export bundle

import argparse
import sys
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ransomeye_correlation.storage.manifest_signer import ManifestSigner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sign_export(export_dir: Path, incident_id: str, output_path: Path):
    """
    Sign export bundle.
    
    Args:
        export_dir: Directory containing export files
        incident_id: Incident identifier
        output_path: Output bundle path
    """
    manifest_signer = ManifestSigner()
    signed_bundle = manifest_signer.sign_export(export_dir, incident_id)
    
    # Move to output path if specified
    if output_path and output_path != signed_bundle:
        import shutil
        shutil.move(str(signed_bundle), str(output_path))
        logger.info(f"Signed bundle saved to: {output_path}")
    else:
        logger.info(f"Signed bundle saved to: {signed_bundle}")

def main():
    parser = argparse.ArgumentParser(description='Sign export bundle')
    parser.add_argument('--export-dir', type=str, required=True,
                       help='Export directory path')
    parser.add_argument('--incident-id', type=str, required=True,
                       help='Incident identifier')
    parser.add_argument('--output', type=str,
                       help='Output bundle path (optional)')
    
    args = parser.parse_args()
    
    try:
        export_dir = Path(args.export_dir)
        output_path = Path(args.output) if args.output else None
        sign_export(export_dir, args.incident_id, output_path)
        return 0
    except Exception as e:
        logger.error(f"Error signing export: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main())

