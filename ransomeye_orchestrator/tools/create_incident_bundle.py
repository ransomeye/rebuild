#!/usr/bin/env python3
# Path and File Name : /home/ransomeye/rebuild/ransomeye_orchestrator/tools/create_incident_bundle.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: CLI tool to manually trigger bundling for an incident ID

import os
import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ransomeye_orchestrator.bundle.bundle_builder import BundleBuilder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Create bundle for an incident')
    parser.add_argument('incident_id', help='Incident identifier')
    parser.add_argument('-o', '--output', help='Output path for bundle', default=None)
    parser.add_argument('-c', '--chunk-size', type=int, default=256, help='Chunk size in MB (default: 256)')
    
    args = parser.parse_args()
    
    try:
        builder = BundleBuilder()
        
        logger.info(f"Creating bundle for incident: {args.incident_id}")
        
        result = builder.create_bundle(
            incident_id=args.incident_id,
            output_path=args.output,
            chunk_size_mb=args.chunk_size
        )
        
        print("\n" + "="*60)
        print("Bundle Created Successfully")
        print("="*60)
        print(f"Bundle Path: {result['bundle_path']}")
        print(f"Bundle Size: {result['bundle_size']:,} bytes ({result['bundle_size'] / 1024 / 1024:.2f} MB)")
        print(f"Bundle Hash: {result['bundle_hash']}")
        print(f"File Count: {result['file_count']}")
        print(f"Compression: {result['compression']}")
        print("="*60 + "\n")
        
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Failed to create bundle: {e}", exc_info=True)
        print(f"\nError: {e}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

