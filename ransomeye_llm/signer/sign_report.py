# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm/signer/sign_report.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Signs generated PDF reports using RSA private key

import os
import json
import hashlib
import base64
from pathlib import Path
from typing import Tuple, Dict, Any
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReportSigner:
    """
    Signs reports and generates manifest files.
    """
    
    def __init__(self, private_key_path: str = None):
        """
        Initialize report signer.
        
        Args:
            private_key_path: Path to RSA private key
        """
        self.private_key_path = Path(private_key_path or os.environ.get(
            'REPORT_SIGN_KEY_PATH',
            '/home/ransomeye/rebuild/certs/report_sign_private.pem'
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
        
        logger.info(f"Generated new report signing key: {self.private_key_path}")
        return private_key
    
    def sign_report(self, pdf_path: Path, job_id: str) -> Tuple[Path, Path]:
        """
        Sign a report PDF and generate manifest.
        
        Args:
            pdf_path: Path to PDF file
            job_id: Job identifier
            
        Returns:
            Tuple of (manifest_path, signature_path)
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Calculate PDF hash
        pdf_hash = self._calculate_file_hash(pdf_path)
        
        # Create manifest
        manifest = {
            'job_id': job_id,
            'pdf_path': str(pdf_path),
            'pdf_hash': pdf_hash,
            'signed_at': self._get_timestamp()
        }
        
        # Save manifest
        manifest_path = pdf_path.parent / f"{pdf_path.stem}_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Sign manifest
        manifest_content = json.dumps(manifest, sort_keys=True).encode()
        signature = self.private_key.sign(
            manifest_content,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Save signature
        signature_path = pdf_path.parent / f"{pdf_path.stem}_manifest.sig"
        with open(signature_path, 'wb') as f:
            f.write(base64.b64encode(signature))
        
        logger.info(f"Report signed: {pdf_path} -> {signature_path}")
        return manifest_path, signature_path
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA256 hash of file.
        
        Args:
            file_path: Path to file
            
        Returns:
            SHA256 hash as hex string
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.utcnow().isoformat() + 'Z'

