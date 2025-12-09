#!/usr/bin/env python3
# Path and File Name : /home/ransomeye/rebuild/ransomeye_orchestrator/tools/verify_bundle.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: CLI tool to check bundle integrity on disk

import os
import sys
import argparse
import logging
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ransomeye_orchestrator.bundle.verifier import BundleVerifier
from ransomeye_orchestrator.bundle.manifest import ManifestGenerator
import tarfile

# Try to import zstandard
try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False
    import gzip

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_bundle(bundle_path: Path, output_dir: Path):
    """Extract bundle archive."""
    if bundle_path.suffix == '.zst' or bundle_path.suffixes[-2:] == ['.tar', '.zst']:
        if not ZSTD_AVAILABLE:
            raise ValueError("zstandard required for .zst bundles")
        dctx = zstd.ZstdDecompressor()
        with open(bundle_path, 'rb') as in_file:
            with dctx.stream_reader(in_file) as reader:
                with tarfile.open(fileobj=reader, mode='r|') as tar:
                    tar.extractall(output_dir)
    elif bundle_path.suffix == '.gz' or bundle_path.suffixes[-2:] == ['.tar', '.gz']:
        with tarfile.open(bundle_path, 'r:gz') as tar:
            tar.extractall(output_dir)
    else:
        raise ValueError(f"Unsupported bundle format: {bundle_path.suffix}")


def main():
    parser = argparse.ArgumentParser(description='Verify bundle integrity')
    parser.add_argument('bundle_path', help='Path to bundle archive')
    parser.add_argument('--no-signature', action='store_true', help='Skip signature verification')
    
    args = parser.parse_args()
    
    bundle_path = Path(args.bundle_path)
    
    if not bundle_path.exists():
        print(f"Error: Bundle not found: {bundle_path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Extract bundle to temp directory
        with tempfile.TemporaryDirectory(prefix="verify_") as temp_dir:
            temp_path = Path(temp_dir)
            bundle_dir = temp_path / "bundle"
            bundle_dir.mkdir()
            
            logger.info(f"Extracting bundle: {bundle_path}")
            extract_bundle(bundle_path, bundle_dir)
            
            # Load manifest
            manifest_path = bundle_dir / "manifest.json"
            if not manifest_path.exists():
                print("Error: Manifest not found in bundle", file=sys.stderr)
                sys.exit(1)
            
            manifest = ManifestGenerator.load_manifest(manifest_path)
            
            # Verify signature if requested
            if not args.no_signature:
                signature_path = bundle_dir / "manifest.sig"
                if not signature_path.exists():
                    print("Warning: Signature file not found", file=sys.stderr)
                else:
                    try:
                        verifier = BundleVerifier()
                        verification_result = verifier.verify_bundle(
                            bundle_dir,
                            manifest_path,
                            signature_path
                        )
                        
                        print("\n" + "="*60)
                        print("Bundle Verification: PASSED")
                        print("="*60)
                        print(f"Files Verified: {verification_result['files_verified']}")
                        print(f"Chunks Verified: {verification_result.get('chunks_verified', 0)}")
                        print(f"Manifest Hash: {verification_result['manifest_hash'][:16]}...")
                        print("="*60 + "\n")
                        
                    except ValueError as e:
                        print(f"\nError: Signature verification failed: {e}\n", file=sys.stderr)
                        sys.exit(1)
            else:
                # Just verify file hashes
                print("\n" + "="*60)
                print("Bundle File Verification")
                print("="*60)
                
                files_ok = 0
                files_failed = 0
                
                for file_info in manifest.get('files', []):
                    file_path = bundle_dir / file_info['path']
                    expected_hash = file_info.get('sha256')
                    
                    if expected_hash and file_path.exists():
                        import hashlib
                        with open(file_path, 'rb') as f:
                            calculated_hash = hashlib.sha256(f.read()).hexdigest()
                        
                        if calculated_hash == expected_hash:
                            files_ok += 1
                        else:
                            files_failed += 1
                            print(f"FAILED: {file_info['path']}")
                
                print(f"Files OK: {files_ok}")
                print(f"Files Failed: {files_failed}")
                print("="*60 + "\n")
                
                if files_failed > 0:
                    sys.exit(1)
        
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Verification failed: {e}", exc_info=True)
        print(f"\nError: {e}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

