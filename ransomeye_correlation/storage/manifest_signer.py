# Path and File Name : /home/ransomeye/rebuild/ransomeye_correlation/storage/manifest_signer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: RSA signing logic for exports using EXPORT_SIGN_KEY_PATH

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

class ManifestSigner:
    """
    Signs export bundles using RSA private key.
    """
    
    def __init__(self, private_key_path: str = None):
        """
        Initialize manifest signer.
        
        Args:
            private_key_path: Path to RSA private key
        """
        self.private_key_path = Path(private_key_path or os.environ.get(
            'EXPORT_SIGN_KEY_PATH',
            '/home/ransomeye/rebuild/certs/export_sign_private.pem'
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
        
        logger.info(f"Generated new export signing key: {self.private_key_path}")
        return private_key
    
    def sign_export(self, export_dir: Path, incident_id: str) -> Path:
        """
        Sign export bundle.
        
        Args:
            export_dir: Directory containing export files
            incident_id: Incident identifier
            
        Returns:
            Path to signed bundle
        """
        export_dir = Path(export_dir)
        
        # Create manifest
        manifest = {
            'incident_id': incident_id,
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'files': {}
        }
        
        # Calculate hashes for all files
        for file_path in export_dir.glob('*'):
            if file_path.is_file():
                file_hash = self._calculate_file_hash(file_path)
                manifest['files'][file_path.name] = file_hash
        
        # Save manifest
        manifest_file = export_dir / "manifest.json"
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
        
        signature_file = export_dir / "manifest.sig"
        with open(signature_file, 'wb') as f:
            f.write(base64.b64encode(signature))
        
        # Create tar.gz bundle
        output_path = Path(f"/tmp/incident_{incident_id}_export.tar.gz")
        with tarfile.open(output_path, 'w:gz') as tar:
            tar.add(export_dir, arcname='.', recursive=True)
        
        logger.info(f"Signed export bundle: {output_path}")
        return output_path
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

