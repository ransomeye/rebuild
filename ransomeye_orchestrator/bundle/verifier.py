# Path and File Name : /home/ransomeye/rebuild/ransomeye_orchestrator/bundle/verifier.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Verifies manifest signature and file hashes (fail-closed)

import os
import json
import base64
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class BundleVerifier:
    """Verifies manifest signature and file hashes (fail-closed)."""
    
    def __init__(self, verify_key_path: str = None):
        """
        Initialize verifier.
        
        Args:
            verify_key_path: Path to public key (default: ORCH_VERIFY_KEY_PATH env var)
        """
        if verify_key_path is None:
            verify_key_path = os.environ.get('ORCH_VERIFY_KEY_PATH', '')
        
        if not verify_key_path or not os.path.exists(verify_key_path):
            raise ValueError(f"Verify key not found: {verify_key_path}")
        
        self.verify_key_path = verify_key_path
        self.public_key = self._load_public_key(verify_key_path)
    
    def _load_public_key(self, key_path: str):
        """Load RSA public key from file."""
        try:
            with open(key_path, 'rb') as f:
                public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )
            logger.info(f"Public key loaded from {key_path}")
            return public_key
        except Exception as e:
            logger.error(f"Failed to load public key: {e}")
            raise
    
    def verify_signature(self, manifest: Dict[str, Any], signature_data: Dict[str, Any]) -> bool:
        """
        Verify manifest signature.
        
        Args:
            manifest: Manifest dictionary
            signature_data: Signature data dictionary
        
        Returns:
            True if signature is valid
        
        Raises:
            ValueError: If signature verification fails (fail-closed)
        """
        signature_b64 = signature_data.get('signature')
        if not signature_b64:
            raise ValueError("Signature missing from signature file")
        
        # Decode signature
        try:
            signature = base64.b64decode(signature_b64)
        except Exception as e:
            raise ValueError(f"Invalid signature encoding: {e}")
        
        # Create canonical JSON (must match signing format)
        manifest_json = json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode('utf-8')
        
        # Verify signature
        try:
            self.public_key.verify(
                signature,
                manifest_json,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            logger.info("Signature verification successful")
            return True
        except Exception as e:
            raise ValueError(f"Signature verification failed: {e}")
    
    def verify_file_hash(self, file_path: Path, expected_hash: str) -> bool:
        """
        Verify file SHA256 hash.
        
        Args:
            file_path: Path to file
            expected_hash: Expected SHA256 hash
        
        Returns:
            True if hash matches
        
        Raises:
            ValueError: If hash verification fails (fail-closed)
        """
        if not file_path.exists():
            raise ValueError(f"File not found: {file_path}")
        
        # Calculate file hash
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(64 * 1024)  # 64KB chunks
                if not chunk:
                    break
                sha256.update(chunk)
        
        calculated_hash = sha256.hexdigest()
        
        if calculated_hash != expected_hash:
            raise ValueError(
                f"File hash mismatch for {file_path}: "
                f"expected {expected_hash[:16]}..., got {calculated_hash[:16]}..."
            )
        
        logger.debug(f"File hash verified: {file_path}")
        return True
    
    def verify_bundle(
        self,
        bundle_dir: Path,
        manifest_path: Path = None,
        signature_path: Path = None
    ) -> Dict[str, Any]:
        """
        Verify entire bundle (signature + all file hashes).
        
        Args:
            bundle_dir: Bundle directory
            manifest_path: Path to manifest.json (default: bundle_dir/manifest.json)
            signature_path: Path to manifest.sig (default: bundle_dir/manifest.sig)
        
        Returns:
            Verification result dictionary
        
        Raises:
            ValueError: If verification fails (fail-closed)
        """
        if manifest_path is None:
            manifest_path = bundle_dir / "manifest.json"
        if signature_path is None:
            signature_path = bundle_dir / "manifest.sig"
        
        # Load manifest
        if not manifest_path.exists():
            raise ValueError(f"Manifest not found: {manifest_path}")
        
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Verify manifest integrity
        manifest_hash = manifest.get('manifest_hash')
        if manifest_hash:
            manifest_copy = manifest.copy()
            manifest_copy.pop('manifest_hash', None)
            manifest_json = json.dumps(manifest_copy, sort_keys=True, separators=(',', ':'))
            calculated_hash = hashlib.sha256(manifest_json.encode('utf-8')).hexdigest()
            if calculated_hash != manifest_hash:
                raise ValueError("Manifest integrity check failed")
        
        # Verify signature
        if not signature_path.exists():
            raise ValueError(f"Signature file not found: {signature_path}")
        
        with open(signature_path, 'r') as f:
            signature_data = json.load(f)
        
        self.verify_signature(manifest, signature_data)
        
        # Verify all files
        files_verified = 0
        files_failed = []
        
        for file_info in manifest.get('files', []):
            file_path = bundle_dir / file_info['path']
            expected_hash = file_info.get('sha256')
            
            if expected_hash:
                try:
                    self.verify_file_hash(file_path, expected_hash)
                    files_verified += 1
                except ValueError as e:
                    files_failed.append(str(e))
        
        # Verify chunks if present
        chunks_verified = 0
        chunks_failed = []
        
        for chunk_info in manifest.get('chunks', []):
            chunk_path = Path(chunk_info['path'])
            if not chunk_path.is_absolute():
                chunk_path = bundle_dir / chunk_path
            
            expected_hash = chunk_info.get('sha256')
            if expected_hash:
                try:
                    self.verify_file_hash(chunk_path, expected_hash)
                    chunks_verified += 1
                except ValueError as e:
                    chunks_failed.append(str(e))
        
        if files_failed or chunks_failed:
            raise ValueError(
                f"Bundle verification failed: "
                f"{len(files_failed)} files failed, {len(chunks_failed)} chunks failed"
            )
        
        result = {
            "verified": True,
            "files_verified": files_verified,
            "chunks_verified": chunks_verified,
            "manifest_hash": manifest_hash
        }
        
        logger.info(f"Bundle verification successful: {files_verified} files, {chunks_verified} chunks")
        return result

