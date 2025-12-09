# Path and File Name : /home/ransomeye/rebuild/ransomeye_ops/key_management/rotate_signing_keys.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Rotates manifest and update signing keys with minimal downtime, generates key update bundle for agents

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend


class SigningKeyRotator:
    """Rotates signing keys for manifests and agent updates."""
    
    def __init__(self, rebuild_root: str = None):
        self.rebuild_root = Path(rebuild_root) if rebuild_root else Path(
            os.environ.get('REBUILD_ROOT', '/home/ransomeye/rebuild')
        )
        self.certs_dir = self.rebuild_root / 'certs'
        self.certs_dir.mkdir(parents=True, exist_ok=True)
        
        self.old_key_name = 'update_signing_key.pem'
        self.new_key_name = 'update_signing_key_new.pem'
        self.backup_key_name = 'update_signing_key_backup.pem'
    
    def generate_key_pair(self) -> Tuple[bytes, bytes]:
        """Generate new RSA key pair."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem, public_pem
    
    def create_key_update_bundle(self, old_key_path: Path, new_public_key: bytes) -> Optional[Path]:
        """Create key update bundle signed with old key for agent distribution."""
        try:
            # Load old private key
            with open(old_key_path, 'rb') as f:
                old_private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
            
            # Create update bundle
            bundle = {
                'timestamp': datetime.now().isoformat(),
                'new_public_key': new_public_key.decode('utf-8'),
                'key_id': hashlib.sha256(new_public_key).hexdigest()[:16],
                'version': '1.0'
            }
            
            bundle_json = json.dumps(bundle, indent=2).encode('utf-8')
            
            # Sign bundle with old key
            signature = old_private_key.sign(
                bundle_json,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            # Create bundle file
            bundle_dir = self.rebuild_root / 'key_updates'
            bundle_dir.mkdir(exist_ok=True)
            bundle_path = bundle_dir / f"key_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            bundle_data = {
                'bundle': bundle,
                'signature': signature.hex(),
                'signed_by': 'old_key'
            }
            
            with open(bundle_path, 'w') as f:
                json.dump(bundle_data, f, indent=2)
            
            return bundle_path
            
        except Exception as e:
            print(f"Failed to create key update bundle: {e}")
            return None
    
    def rotate_keys(self, create_bundle: bool = True) -> bool:
        """Rotate signing keys with minimal downtime."""
        try:
            print("Rotating signing keys...")
            
            old_key_path = self.certs_dir / self.old_key_name
            new_key_path = self.certs_dir / self.new_key_name
            
            # Step 1: Generate new key pair
            print("  [1/4] Generating new key pair...")
            new_private_pem, new_public_pem = self.generate_key_pair()
            
            # Save new keys
            with open(new_key_path, 'wb') as f:
                f.write(new_private_pem)
            os.chmod(new_key_path, 0o600)
            
            new_pubkey_path = new_key_path.with_suffix('.pub')
            with open(new_pubkey_path, 'wb') as f:
                f.write(new_public_pem)
            
            print(f"  ✓ New keys generated: {new_key_path}")
            
            # Step 2: Create update bundle (if old key exists)
            if old_key_path.exists() and create_bundle:
                print("  [2/4] Creating key update bundle...")
                bundle_path = self.create_key_update_bundle(old_key_path, new_public_pem)
                if bundle_path:
                    print(f"  ✓ Update bundle created: {bundle_path}")
                else:
                    print("  WARNING: Failed to create update bundle")
            
            # Step 3: Backup old key
            if old_key_path.exists():
                print("  [3/4] Backing up old key...")
                backup_path = self.certs_dir / self.backup_key_name
                shutil.copy2(old_key_path, backup_path)
                old_pubkey_path = old_key_path.with_suffix('.pub')
                if old_pubkey_path.exists():
                    shutil.copy2(old_pubkey_path, backup_path.with_suffix('.pub'))
                print(f"  ✓ Old key backed up: {backup_path}")
            
            # Step 4: Activate new key
            print("  [4/4] Activating new key...")
            if old_key_path.exists():
                # Rename old key
                old_key_backup = self.certs_dir / f"{self.old_key_name}.old"
                shutil.move(str(old_key_path), str(old_key_backup))
            
            # Move new key to active position
            shutil.move(str(new_key_path), str(old_key_path))
            shutil.move(str(new_pubkey_path), str(old_key_path.with_suffix('.pub')))
            
            print(f"  ✓ New key activated: {old_key_path}")
            
            print("\n✓ Key rotation completed successfully")
            print(f"  Old key backup: {self.certs_dir / self.backup_key_name}")
            if create_bundle and old_key_path.exists():
                print(f"  Update bundle: {self.rebuild_root / 'key_updates'}")
            
            return True
            
        except Exception as e:
            print(f"\n✗ Key rotation failed: {e}")
            return False
    
    def rollback(self) -> bool:
        """Rollback to previous key."""
        try:
            print("Rolling back key rotation...")
            
            old_key_path = self.certs_dir / self.old_key_name
            backup_path = self.certs_dir / self.backup_key_name
            
            if not backup_path.exists():
                print("ERROR: Backup key not found")
                return False
            
            # Restore backup
            shutil.copy2(backup_path, old_key_path)
            backup_pubkey = backup_path.with_suffix('.pub')
            if backup_pubkey.exists():
                shutil.copy2(backup_pubkey, old_key_path.with_suffix('.pub'))
            
            print("✓ Key rollback completed")
            return True
            
        except Exception as e:
            print(f"✗ Rollback failed: {e}")
            return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Rotate signing keys for manifests and updates')
    parser.add_argument('--no-bundle', action='store_true', help='Skip creating key update bundle')
    parser.add_argument('--rollback', action='store_true', help='Rollback to previous key')
    
    args = parser.parse_args()
    
    rotator = SigningKeyRotator()
    
    if args.rollback:
        success = rotator.rollback()
    else:
        success = rotator.rotate_keys(create_bundle=not args.no_bundle)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

