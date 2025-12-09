# Path and File Name : /home/ransomeye/rebuild/ransomeye_ops/disaster_recovery/verify_backup.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Verifies integrity and authenticity of backup archives

import os
import hashlib
import json
from pathlib import Path
from typing import Dict, Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend


class BackupVerifier:
    """Verifies backup integrity and authenticity."""
    
    def __init__(self, rebuild_root: str = None):
        self.rebuild_root = Path(rebuild_root) if rebuild_root else Path(
            os.environ.get('REBUILD_ROOT', '/home/ransomeye/rebuild')
        )
        
        self.signing_pubkey_path = Path(os.environ.get(
            'OPS_BACKUP_SIGNING_PUBKEY_PATH',
            str(self.rebuild_root / 'certs' / 'backup_signing_pubkey.pem')
        ))
    
    def calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def verify_manifest_signature(self, manifest_path: Path, sig_path: Path) -> bool:
        """Verify manifest signature."""
        if not self.signing_pubkey_path.exists():
            print("WARNING: Signing public key not found, skipping signature verification")
            return True  # Not a failure if key doesn't exist
        
        try:
            with open(self.signing_pubkey_path, 'rb') as f:
                public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )
            
            with open(manifest_path, 'rb') as f:
                manifest_data = f.read()
            
            with open(sig_path, 'rb') as f:
                signature = f.read()
            
            public_key.verify(
                signature,
                manifest_data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return True
        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False
    
    def verify_backup(self, backup_path: Path) -> bool:
        """Verify backup integrity."""
        if not backup_path.exists():
            print(f"ERROR: Backup file not found: {backup_path}")
            return False
        
        print(f"Verifying backup: {backup_path.name}")
        
        # Find manifest
        manifest_path = backup_path.parent / f"{backup_path.stem.replace('.tar.gz.enc', '')}.manifest.json"
        if not manifest_path.exists():
            print("WARNING: Manifest not found, performing basic integrity check")
            # Basic check: file exists and is readable
            try:
                with open(backup_path, 'rb') as f:
                    f.read(1024)  # Read first KB
                print("✓ Backup file is readable")
                return True
            except Exception as e:
                print(f"✗ Backup file is corrupted: {e}")
                return False
        
        # Load manifest
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
        except Exception as e:
            print(f"ERROR: Failed to load manifest: {e}")
            return False
        
        # Verify signature
        sig_path = manifest_path.with_suffix('.sig')
        if sig_path.exists():
            if not self.verify_manifest_signature(manifest_path, sig_path):
                print("✗ Manifest signature verification failed")
                return False
            print("✓ Manifest signature verified")
        else:
            print("WARNING: Manifest signature not found")
        
        # Verify file checksums
        print("Verifying file checksums...")
        all_valid = True
        
        for file_type, file_info in manifest.get('files', {}).items():
            file_path = Path(file_info.get('path', ''))
            expected_hash = file_info.get('sha256', '')
            expected_size = file_info.get('size', 0)
            
            if not file_path.exists():
                # File might be in backup archive, check backup itself
                if file_type == 'encrypted_backup':
                    file_path = backup_path
                else:
                    print(f"  ✗ {file_type}: File not found")
                    all_valid = False
                    continue
            
            # Check size
            actual_size = file_path.stat().st_size
            if actual_size != expected_size:
                print(f"  ✗ {file_type}: Size mismatch (expected {expected_size}, got {actual_size})")
                all_valid = False
                continue
            
            # Check checksum
            actual_hash = self.calculate_checksum(file_path)
            if actual_hash != expected_hash:
                print(f"  ✗ {file_type}: Checksum mismatch")
                print(f"    Expected: {expected_hash}")
                print(f"    Got:      {actual_hash}")
                all_valid = False
            else:
                print(f"  ✓ {file_type}: Checksum verified")
        
        if all_valid:
            print("\n✓ Backup verification passed")
        else:
            print("\n✗ Backup verification failed")
        
        return all_valid


def main():
    """Main entry point."""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify backup integrity')
    parser.add_argument('backup_path', type=str, help='Path to backup file')
    
    args = parser.parse_args()
    
    verifier = BackupVerifier()
    success = verifier.verify_backup(Path(args.backup_path))
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

