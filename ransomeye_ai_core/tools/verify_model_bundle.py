# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_core/tools/verify_model_bundle.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: CLI tool to verify model bundle integrity (signature and hashes)

import argparse
import tarfile
import json
import base64
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ransomeye_ai_core.loader.model_validator import ModelValidator, ModelValidationError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_bundle(bundle_path: Path, verify_key_path: Path = None):
    """
    Verify a model bundle's integrity.
    
    Args:
        bundle_path: Path to .tar.gz bundle
        verify_key_path: Optional path to public key (uses MODEL_VERIFY_KEY_PATH env var if not provided)
    """
    bundle_path = Path(bundle_path)
    
    if not bundle_path.exists():
        raise ValueError(f"Bundle file not found: {bundle_path}")
    
    logger.info(f"Verifying bundle: {bundle_path}")
    
    # Initialize validator
    validator = ModelValidator(verify_key_path=str(verify_key_path) if verify_key_path else None)
    
    # Validate bundle
    try:
        result = validator.validate_bundle(bundle_path)
        
        logger.info("✓ Bundle validation successful")
        logger.info(f"  Extracted to: {result['extract_dir']}")
        logger.info(f"  Manifest: {result['manifest'].get('metadata', {}).get('name', 'unknown')}")
        logger.info(f"  Version: {result['manifest'].get('metadata', {}).get('version', 'unknown')}")
        
        return 0
        
    except ModelValidationError as e:
        logger.error(f"✗ Bundle validation failed: {e}")
        return 1
    except Exception as e:
        logger.error(f"✗ Error verifying bundle: {e}")
        return 1

def main():
    parser = argparse.ArgumentParser(description='Verify model bundle integrity')
    parser.add_argument('--bundle', type=str, required=True,
                       help='Path to model bundle (.tar.gz)')
    parser.add_argument('--key', type=str, default=None,
                       help='Path to RSA public key for signature verification')
    
    args = parser.parse_args()
    
    try:
        return verify_bundle(
            Path(args.bundle),
            Path(args.key) if args.key else None
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())

