# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_core/loader/model_validator.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Model bundle validation with crypto-signature and hash verification

import os
import json
import hashlib
import shutil
import tempfile
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelValidationError(Exception):
    """Custom exception for model validation errors."""
    pass

class ModelValidator:
    """Validates model bundles with signature and hash verification."""
    
    def __init__(self, verify_key_path: str = None):
        """
        Initialize validator.
        
        Args:
            verify_key_path: Path to RSA public key for signature verification
        """
        self.verify_key_path = verify_key_path or os.environ.get(
            'MODEL_VERIFY_KEY_PATH',
            '/home/ransomeye/rebuild/certs/model_verify_public.pem'
        )
        self.public_key = None
        self._load_public_key()
    
    def _load_public_key(self):
        """Load RSA public key for signature verification."""
        if not os.path.exists(self.verify_key_path):
            logger.warning(f"Public key not found at {self.verify_key_path}, signature verification will fail")
            return
        
        try:
            with open(self.verify_key_path, 'rb') as f:
                self.public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )
            logger.info(f"Loaded public key from {self.verify_key_path}")
        except Exception as e:
            logger.error(f"Failed to load public key: {e}")
            raise ModelValidationError(f"Failed to load public key: {e}")
    
    def calculate_sha256(self, file_path: Path) -> str:
        """
        Calculate SHA256 hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            SHA256 hash as hex string
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def verify_signature(self, manifest_path: Path, signature_path: Path) -> bool:
        """
        Verify RSA signature of manifest.json.
        
        Args:
            manifest_path: Path to manifest.json
            signature_path: Path to manifest.sig
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.public_key:
            raise ModelValidationError("Public key not loaded, cannot verify signature")
        
        if not manifest_path.exists():
            raise ModelValidationError(f"Manifest file not found: {manifest_path}")
        
        if not signature_path.exists():
            raise ModelValidationError(f"Signature file not found: {signature_path}")
        
        try:
            # Read manifest content
            with open(manifest_path, 'rb') as f:
                manifest_content = f.read()
            
            # Read signature
            import base64
            with open(signature_path, 'r') as f:
                signature_b64 = f.read().strip()
                signature = base64.b64decode(signature_b64)
            
            # Verify signature
            try:
                self.public_key.verify(
                    signature,
                    manifest_content,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
                logger.info("Signature verification successful")
                return True
            except Exception as e:
                logger.error(f"Signature verification failed: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error during signature verification: {e}")
            raise ModelValidationError(f"Signature verification error: {e}")
    
    def verify_manifest_hashes(self, extract_dir: Path, manifest: dict) -> bool:
        """
        Verify that all files in manifest match their SHA256 hashes.
        
        Args:
            extract_dir: Directory containing extracted files
            manifest: Parsed manifest.json dictionary
            
        Returns:
            True if all hashes match, False otherwise
        """
        if 'files' not in manifest:
            raise ModelValidationError("Manifest missing 'files' section")
        
        all_valid = True
        for file_path, expected_hash in manifest['files'].items():
            full_path = extract_dir / file_path
            
            if not full_path.exists():
                logger.error(f"File in manifest does not exist: {file_path}")
                all_valid = False
                continue
            
            # Security check: ensure file is within extract_dir
            try:
                full_path.resolve().relative_to(extract_dir.resolve())
            except ValueError:
                logger.error(f"File path outside extract directory: {file_path}")
                all_valid = False
                continue
            
            actual_hash = self.calculate_sha256(full_path)
            
            if actual_hash != expected_hash:
                logger.error(f"Hash mismatch for {file_path}: expected {expected_hash}, got {actual_hash}")
                all_valid = False
            else:
                logger.debug(f"Hash verified for {file_path}")
        
        return all_valid
    
    def validate_bundle(self, bundle_path: Path, extract_to: Path = None) -> dict:
        """
        Validate a model bundle: extract, verify signature, verify hashes.
        
        Args:
            bundle_path: Path to .tar.gz bundle
            extract_to: Directory to extract to (creates temp dir if not provided)
            
        Returns:
            Dictionary with validation results and extracted path
            
        Raises:
            ModelValidationError: If validation fails
        """
        import tarfile
        
        if not bundle_path.exists():
            raise ModelValidationError(f"Bundle file not found: {bundle_path}")
        
        # Create temporary extraction directory if not provided
        temp_dir = None
        if extract_to is None:
            temp_dir = tempfile.mkdtemp(prefix='model_validation_')
            extract_to = Path(temp_dir)
        else:
            extract_to = Path(extract_to)
            extract_to.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"Validating bundle: {bundle_path}")
            
            # Extract bundle
            logger.info(f"Extracting bundle to {extract_to}")
            with tarfile.open(bundle_path, 'r:gz') as tar:
                tar.extractall(extract_to)
            
            # Find manifest.json and manifest.sig
            manifest_path = extract_to / "manifest.json"
            signature_path = extract_to / "manifest.sig"
            
            if not manifest_path.exists():
                raise ModelValidationError("manifest.json not found in bundle")
            
            if not signature_path.exists():
                raise ModelValidationError("manifest.sig not found in bundle - signature verification required")
            
            # Load manifest
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            # Verify signature
            logger.info("Verifying signature...")
            if not self.verify_signature(manifest_path, signature_path):
                raise ModelValidationError("Signature verification failed - bundle is not authentic")
            
            # Verify file hashes
            logger.info("Verifying file hashes...")
            if not self.verify_manifest_hashes(extract_to, manifest):
                raise ModelValidationError("File hash verification failed - bundle may be corrupted")
            
            logger.info("Bundle validation successful")
            
            return {
                'valid': True,
                'extract_dir': str(extract_to),
                'manifest': manifest,
                'temp_dir': temp_dir is not None
            }
            
        except Exception as e:
            # Clean up on failure
            if temp_dir and Path(temp_dir).exists():
                logger.info(f"Cleaning up temporary directory: {temp_dir}")
                shutil.rmtree(temp_dir, ignore_errors=True)
            
            if isinstance(e, ModelValidationError):
                raise
            else:
                raise ModelValidationError(f"Validation error: {e}")

