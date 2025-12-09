# Path and File Name : /home/ransomeye/rebuild/ransomeye_ops/key_management/cert_renewer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Regenerates self-signed mTLS certificates before expiry

import os
import sys
import ipaddress
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


class CertRenewer:
    """Renews self-signed mTLS certificates."""
    
    def __init__(self, rebuild_root: str = None):
        self.rebuild_root = Path(rebuild_root) if rebuild_root else Path(
            os.environ.get('REBUILD_ROOT', '/home/ransomeye/rebuild')
        )
        self.certs_dir = self.rebuild_root / 'certs'
        self.certs_dir.mkdir(parents=True, exist_ok=True)
        
        self.cert_path = self.certs_dir / 'cert.pem'
        self.key_path = self.certs_dir / 'key.pem'
        self.days_before_expiry = 30  # Renew 30 days before expiry
    
    def load_certificate(self) -> Optional[x509.Certificate]:
        """Load existing certificate."""
        if not self.cert_path.exists():
            return None
        
        try:
            with open(self.cert_path, 'rb') as f:
                cert_data = f.read()
                cert = x509.load_pem_x509_certificate(cert_data, default_backend())
                return cert
        except Exception as e:
            print(f"Error loading certificate: {e}")
            return None
    
    def is_cert_expiring_soon(self, cert: x509.Certificate) -> bool:
        """Check if certificate is expiring within threshold."""
        expiry_date = cert.not_valid_after
        threshold_date = datetime.now() + timedelta(days=self.days_before_expiry)
        
        return expiry_date < threshold_date
    
    def generate_certificate(self, days_valid: int = 365) -> Tuple[bytes, bytes]:
        """Generate new self-signed certificate."""
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Create certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "RansomEye"),
            x509.NameAttribute(NameOID.COMMON_NAME, "ransomeye.local"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now()
        ).not_valid_after(
            datetime.now() + timedelta(days=days_valid)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("ransomeye.local"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256(), default_backend())
        
        # Serialize
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        return cert_pem, key_pem
    
    def renew_certificate(self, force: bool = False) -> bool:
        """Renew certificate if expiring soon."""
        try:
            existing_cert = self.load_certificate()
            
            if existing_cert and not force:
                if not self.is_cert_expiring_soon(existing_cert):
                    expiry_date = existing_cert.not_valid_after
                    days_remaining = (expiry_date - datetime.now()).days
                    print(f"Certificate is valid for {days_remaining} more days. No renewal needed.")
                    return True
                
                print(f"Certificate expires on {existing_cert.not_valid_after}. Renewing...")
            
            # Backup existing certs
            if self.cert_path.exists():
                backup_cert = self.cert_path.with_suffix('.pem.backup')
                import shutil
                shutil.copy2(self.cert_path, backup_cert)
                print(f"Backed up existing certificate: {backup_cert}")
            
            if self.key_path.exists():
                backup_key = self.key_path.with_suffix('.pem.backup')
                import shutil
                shutil.copy2(self.key_path, backup_key)
                print(f"Backed up existing key: {backup_key}")
            
            # Generate new certificate
            print("Generating new certificate...")
            cert_pem, key_pem = self.generate_certificate()
            
            # Write new certificate
            with open(self.cert_path, 'wb') as f:
                f.write(cert_pem)
            os.chmod(self.cert_path, 0o644)
            
            with open(self.key_path, 'wb') as f:
                f.write(key_pem)
            os.chmod(self.key_path, 0o600)
            
            print(f"✓ New certificate generated: {self.cert_path}")
            print(f"✓ New key generated: {self.key_path}")
            
            # Restart services that use the certificate
            print("Restarting services...")
            import subprocess
            services = [
                'ransomeye-core.service',
                'ransomeye-ai-core.service',
            ]
            
            for service in services:
                try:
                    subprocess.run(
                        ['systemctl', 'restart', service],
                        check=False,
                        capture_output=True,
                        timeout=30
                    )
                except Exception:
                    pass
            
            print("✓ Certificate renewal completed")
            return True
            
        except Exception as e:
            print(f"✗ Certificate renewal failed: {e}")
            return False


def main():
    """Main entry point."""
    import argparse
    import ipaddress
    
    parser = argparse.ArgumentParser(description='Renew self-signed mTLS certificates')
    parser.add_argument('--force', action='store_true', help='Force renewal even if not expiring')
    
    args = parser.parse_args()
    
    renewer = CertRenewer()
    success = renewer.renew_certificate(force=args.force)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

