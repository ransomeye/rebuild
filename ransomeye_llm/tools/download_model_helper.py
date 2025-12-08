# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm/tools/download_model_helper.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Script to help operator vendor a GGUF model with hash verification

import argparse
import hashlib
import sys
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_file_hash(file_path: Path, algorithm: str = 'sha256') -> str:
    """
    Calculate hash of file.
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm (sha256, md5)
        
    Returns:
        Hash as hex string
    """
    hash_obj = hashlib.sha256() if algorithm == 'sha256' else hashlib.md5()
    
    with open(file_path, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            hash_obj.update(byte_block)
    
    return hash_obj.hexdigest()

def verify_model_hash(model_path: Path, expected_hash: str) -> bool:
    """
    Verify model file hash.
    
    Args:
        model_path: Path to model file
        expected_hash: Expected hash value
        
    Returns:
        True if hash matches, False otherwise
    """
    if not model_path.exists():
        logger.error(f"Model file not found: {model_path}")
        return False
    
    logger.info(f"Calculating hash for {model_path}...")
    actual_hash = calculate_file_hash(model_path)
    
    if actual_hash.lower() == expected_hash.lower():
        logger.info("✓ Model hash matches expected value")
        return True
    else:
        logger.error(f"✗ Model hash mismatch!")
        logger.error(f"  Expected: {expected_hash}")
        logger.error(f"  Actual:   {actual_hash}")
        return False

def download_model(url: str, output_path: Path, expected_hash: str = None):
    """
    Download model from URL (helper function - requires requests or urllib).
    
    Args:
        url: URL to download from
        output_path: Path to save model
        expected_hash: Optional expected hash for verification
    """
    try:
        import urllib.request
        
        logger.info(f"Downloading model from {url}...")
        logger.info(f"Output: {output_path}")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Download with progress
        def show_progress(block_num, block_size, total_size):
            if total_size > 0:
                percent = min(100, (block_num * block_size * 100) // total_size)
                print(f"\rProgress: {percent}%", end='', flush=True)
        
        urllib.request.urlretrieve(url, output_path, show_progress)
        print()  # New line after progress
        
        logger.info(f"Downloaded: {output_path}")
        
        # Verify hash if provided
        if expected_hash:
            if verify_model_hash(output_path, expected_hash):
                logger.info("✓ Model downloaded and verified successfully")
            else:
                logger.error("✗ Model hash verification failed")
                output_path.unlink()  # Delete invalid file
                return False
        
        return True
        
    except ImportError:
        logger.error("urllib not available. Please download manually:")
        logger.error(f"  URL: {url}")
        logger.error(f"  Output: {output_path}")
        if expected_hash:
            logger.error(f"  Expected SHA256: {expected_hash}")
        return False
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Download and verify GGUF model')
    parser.add_argument('--url', type=str, help='URL to download model from')
    parser.add_argument('--output', type=str, required=True,
                       help='Output path for model file')
    parser.add_argument('--hash', type=str, help='Expected SHA256 hash')
    parser.add_argument('--verify', type=str, help='Verify existing model file hash')
    
    args = parser.parse_args()
    
    output_path = Path(args.output)
    
    if args.verify:
        # Verify existing file
        if verify_model_hash(output_path, args.verify):
            return 0
        else:
            return 1
    
    if args.url:
        # Download model
        if download_model(args.url, output_path, args.hash):
            return 0
        else:
            return 1
    
    # Just calculate hash
    if output_path.exists():
        hash_value = calculate_file_hash(output_path)
        logger.info(f"SHA256 hash: {hash_value}")
        return 0
    else:
        logger.error(f"File not found: {output_path}")
        return 1

if __name__ == "__main__":
    exit(main())

