# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant/feedback/bundle_exporter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Packages feedback into signed .tar.gz bundle

import os
import json
import tarfile
import hashlib
import base64
from pathlib import Path
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BundleExporter:
    """
    Exports feedback data as signed training bundle.
    """
    
    def __init__(self, private_key_path: str = None):
        """
        Initialize bundle exporter.
        
        Args:
            private_key_path: Path to RSA private key for signing
        """
        self.private_key_path = Path(private_key_path or os.environ.get(
            'FEEDBACK_SIGN_KEY_PATH',
            '/home/ransomeye/rebuild/certs/feedback_sign_private.pem'
        ))
        self.private_key = self._load_or_generate_key()
    
    def _load_or_generate_key(self):
        """Load or generate RSA private key."""
        if self.private_key_path.exists():
            try:
                with open(self.private_key_path, 'rb') as f:
                    return serialization.load_pem_private_key(
                        f.read(),
                        password=None,
                        backend=default_backend()
                    )
            except Exception as e:
                logger.warning(f"Failed to load private key: {e}, generating new key")
        
        # Generate new key (RSA-4096)
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )
        
        # Save private key
        self.private_key_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.private_key_path, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        os.chmod(self.private_key_path, 0o600)
        
        logger.info(f"Generated new feedback signing key: {self.private_key_path}")
        return private_key
    
    def export_bundle(self, feedback_data: list, output_path: Path) -> Path:
        """
        Export feedback data as signed bundle.
        
        Args:
            feedback_data: List of feedback records
            output_path: Output bundle path
            
        Returns:
            Path to created bundle
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create temporary directory
        temp_dir = Path(f"/tmp/feedback_bundle_{output_path.stem}")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Save feedback data
            feedback_file = temp_dir / "feedback_data.json"
            with open(feedback_file, 'w') as f:
                json.dump(feedback_data, f, indent=2)
            
            # Create manifest
            manifest = {
                'bundle_type': 'feedback_training',
                'record_count': len(feedback_data),
                'created_at': datetime.utcnow().isoformat() + 'Z',
                'files': {
                    'feedback_data.json': self._calculate_file_hash(feedback_file)
                }
            }
            
            manifest_file = temp_dir / "manifest.json"
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            # Sign manifest
            with open(manifest_file, 'rb') as f:
                manifest_content = f.read()
            
            signature = self.private_key.sign(
                manifest_content,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            signature_file = temp_dir / "manifest.sig"
            with open(signature_file, 'wb') as f:
                f.write(base64.b64encode(signature))
            
            # Create tar.gz bundle
            with tarfile.open(output_path, 'w:gz') as tar:
                tar.add(temp_dir, arcname='.', recursive=True)
            
            logger.info(f"Feedback bundle exported: {output_path} ({len(feedback_data)} records)")
            return output_path
            
        finally:
            # Cleanup
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

