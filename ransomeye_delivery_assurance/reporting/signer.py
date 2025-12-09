# Path and File Name : /home/ransomeye/rebuild/ransomeye_delivery_assurance/reporting/signer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality: Signs the handover report PDF using RSA-PSS signature with key from AUDIT_SIGN_KEY_PATH

import os
import hashlib
import base64
from pathlib import Path
from typing import Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend


class ReportSigner:
    """Signs PDF reports with cryptographic signatures."""
    
    def __init__(self, key_path: Optional[str] = None):
        self.key_path = Path(key_path) if key_path else None
        if not key_path:
            self.key_path = Path(os.environ.get(
                'AUDIT_SIGN_KEY_PATH',
                '/home/ransomeye/rebuild/certs/audit_signing_key.pem'
            ))
        self.private_key = None
        self.public_key = None
        
    def load_or_generate_key(self) -> None:
        """Load existing key or generate new one."""
        if self.key_path.exists():
            try:
                with open(self.key_path, 'rb') as f:
                    self.private_key = serialization.load_pem_private_key(
                        f.read(),
                        password=None,
                        backend=default_backend()
                    )
                self.public_key = self.private_key.public_key()
                print(f"Loaded signing key from {self.key_path}")
            except Exception as e:
                print(f"Error loading key: {e}")
                print("Generating new key pair...")
                self._generate_key_pair()
        else:
            print(f"Key not found at {self.key_path}, generating new key pair...")
            self._generate_key_pair()
    
    def _generate_key_pair(self) -> None:
        """Generate new RSA key pair."""
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
        
        # Save private key
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        pem_private = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        with open(self.key_path, 'wb') as f:
            f.write(pem_private)
        os.chmod(self.key_path, 0o600)
        print(f"Generated and saved private key to {self.key_path}")
        
        # Save public key
        pub_key_path = self.key_path.with_suffix('.pub')
        pem_public = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        with open(pub_key_path, 'wb') as f:
            f.write(pem_public)
        print(f"Saved public key to {pub_key_path}")
    
    def sign_file(self, file_path: Path) -> tuple[str, str]:
        """Sign a file and return signature and hash."""
        if not self.private_key:
            self.load_or_generate_key()
        
        # Read file content
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # Compute SHA-256 hash
        file_hash = hashlib.sha256(file_content).digest()
        file_hash_b64 = base64.b64encode(file_hash).decode('utf-8')
        
        # Sign hash with RSA-PSS
        signature = self.private_key.sign(
            file_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        return signature_b64, file_hash_b64
    
    def verify_signature(self, file_path: Path, signature_b64: str, expected_hash_b64: str) -> bool:
        """Verify file signature."""
        if not self.public_key:
            # Try to load public key
            pub_key_path = self.key_path.with_suffix('.pub')
            if pub_key_path.exists():
                with open(pub_key_path, 'rb') as f:
                    self.public_key = serialization.load_pem_public_key(
                        f.read(),
                        backend=default_backend()
                    )
            else:
                raise ValueError("Public key not found for verification")
        
        # Read file content
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # Compute hash
        file_hash = hashlib.sha256(file_content).digest()
        file_hash_b64 = base64.b64encode(file_hash).decode('utf-8')
        
        if file_hash_b64 != expected_hash_b64:
            return False
        
        # Verify signature
        signature = base64.b64decode(signature_b64)
        try:
            self.public_key.verify(
                signature,
                file_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False
    
    def create_signature_file(self, pdf_path: Path, signature_b64: str, hash_b64: str) -> Path:
        """Create a signature metadata file."""
        sig_file = pdf_path.with_suffix('.pdf.sig')
        
        sig_content = f"""RansomEye Delivery Assurance Report Signature
==========================================
File: {pdf_path.name}
Hash (SHA-256): {hash_b64}
Signature (RSA-PSS): {signature_b64}
Algorithm: RSA-4096 with PSS padding, SHA-256
Generated: {os.environ.get('TZ', 'UTC')}
"""
        
        with open(sig_file, 'w') as f:
            f.write(sig_content)
        
        return sig_file


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: signer.py <pdf_file> [key_path]")
        sys.exit(1)
    
    pdf_path = Path(sys.argv[1])
    key_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    signer = ReportSigner(key_path)
    signature, file_hash = signer.sign_file(pdf_path)
    sig_file = signer.create_signature_file(pdf_path, signature, file_hash)
    
    print(f"Signed: {pdf_path}")
    print(f"Signature file: {sig_file}")
    print(f"Hash: {file_hash}")
    print(f"Signature: {signature[:50]}...")

