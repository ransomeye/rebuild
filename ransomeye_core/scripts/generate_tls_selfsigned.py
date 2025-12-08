# Path and File Name : /home/ransomeye/rebuild/ransomeye_core/scripts/generate_tls_selfsigned.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Generate self-signed TLS certificates for RansomEye Core API

import argparse
import os
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

def generate_self_signed_cert(cert_path, key_path, common_name="ransomeye.local", 
                              organization="RansomEye", validity_days=365):
    """Generate self-signed TLS certificate and private key."""
    
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
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
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
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=validity_days)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName("127.0.0.1"),
            x509.IPAddress(x509.IPv4Address("127.0.0.1")),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256(), default_backend())
    
    # Save private key
    os.makedirs(os.path.dirname(key_path), exist_ok=True)
    with open(key_path, 'wb') as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    os.chmod(key_path, 0o600)
    
    # Save certificate
    os.makedirs(os.path.dirname(cert_path), exist_ok=True)
    with open(cert_path, 'wb') as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    os.chmod(cert_path, 0o644)
    
    return cert, private_key

def main():
    parser = argparse.ArgumentParser(description='Generate self-signed TLS certificate')
    parser.add_argument('--cert-path', type=str, required=True, help='Certificate file path')
    parser.add_argument('--key-path', type=str, required=True, help='Private key file path')
    parser.add_argument('--common-name', type=str, default='ransomeye.local', help='Common name for certificate')
    parser.add_argument('--organization', type=str, default='RansomEye', help='Organization name')
    parser.add_argument('--validity-days', type=int, default=365, help='Certificate validity in days')
    
    args = parser.parse_args()
    
    # Check if files already exist
    if os.path.exists(args.cert_path) and os.path.exists(args.key_path):
        print(f"Certificate files already exist:")
        print(f"  Certificate: {args.cert_path}")
        print(f"  Private key: {args.key_path}")
        print("Skipping generation. Use --force to overwrite.")
        return 0
    
    try:
        print(f"Generating self-signed TLS certificate...")
        print(f"  Common Name: {args.common_name}")
        print(f"  Organization: {args.organization}")
        print(f"  Validity: {args.validity_days} days")
        
        cert, private_key = generate_self_signed_cert(
            args.cert_path,
            args.key_path,
            args.common_name,
            args.organization,
            args.validity_days
        )
        
        print(f"✓ Certificate generated successfully")
        print(f"  Certificate: {args.cert_path}")
        print(f"  Private key: {args.key_path}")
        print(f"  Valid until: {cert.not_valid_after}")
        
        return 0
    except Exception as e:
        print(f"Error generating certificate: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())

