# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant_advanced/feedback/feedback_exporter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Feedback exporter that creates signed training bundles for offline model improvement

import os
import tarfile
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logging.warning("cryptography not available - signatures disabled")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FeedbackExporter:
    """Exporter for signed feedback bundles."""
    
    def __init__(self, private_key_path: Optional[str] = None):
        """
        Initialize feedback exporter.
        
        Args:
            private_key_path: Path to RSA private key for signing
        """
        self.private_key_path = private_key_path or os.environ.get('SIGNING_KEY_PATH', None)
        self.private_key = None
        
        if CRYPTO_AVAILABLE and self.private_key_path:
            self._load_private_key()
    
    def _load_private_key(self):
        """Load RSA private key."""
        if not self.private_key_path or not Path(self.private_key_path).exists():
            logger.warning("Private key not found - bundles will not be signed")
            return
        
        try:
            from cryptography.hazmat.primitives import serialization
            
            with open(self.private_key_path, 'rb') as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
            logger.info(f"Loaded signing key from {self.private_key_path}")
        except Exception as e:
            logger.error(f"Error loading private key: {e}")
    
    def export_bundle(self, feedback_dir: str, output_path: str) -> str:
        """
        Export feedback as signed training bundle.
        
        Args:
            feedback_dir: Directory containing feedback files
            output_path: Output bundle path (.tar.gz)
            
        Returns:
            Path to created bundle
        """
        feedback_path = Path(feedback_dir)
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Collect feedback files
        feedback_files = list(feedback_path.glob("*.json"))
        
        if not feedback_files:
            logger.warning("No feedback files found")
            return None
        
        # Create manifest
        manifest = {
            'version': '1.0',
            'timestamp': datetime.utcnow().isoformat(),
            'file_count': len(feedback_files),
            'files': []
        }
        
        # Calculate hashes
        for feedback_file in feedback_files:
            file_hash = self._calculate_hash(feedback_file)
            manifest['files'].append({
                'filename': feedback_file.name,
                'sha256': file_hash
            })
        
        # Create bundle
        with tarfile.open(output_file, 'w:gz') as tar:
            # Add feedback files
            for feedback_file in feedback_files:
                tar.add(feedback_file, arcname=feedback_file.name)
            
            # Add manifest
            manifest_json = json.dumps(manifest, indent=2)
            manifest_bytes = manifest_json.encode('utf-8')
            
            # Write manifest to temp file and add to tar
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
                tmp.write(manifest_json)
                tmp_path = tmp.name
            
            tar.add(tmp_path, arcname='manifest.json')
            os.unlink(tmp_path)
            
            # Sign manifest if key available
            if self.private_key:
                signature = self._sign_data(manifest_bytes)
                sig_path = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.sig')
                sig_path.write(signature)
                sig_path.close()
                
                tar.add(sig_path.name, arcname='manifest.sig')
                os.unlink(sig_path.name)
        
        logger.info(f"Exported feedback bundle: {output_file} ({len(feedback_files)} files)")
        return str(output_file)
    
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _sign_data(self, data: bytes) -> bytes:
        """
        Sign data with RSA private key.
        
        Args:
            data: Data to sign
            
        Returns:
            Signature bytes
        """
        if not self.private_key:
            return b''
        
        try:
            signature = self.private_key.sign(
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return signature
        except Exception as e:
            logger.error(f"Error signing data: {e}")
            return b''

