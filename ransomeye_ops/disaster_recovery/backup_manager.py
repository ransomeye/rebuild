# Path and File Name : /home/ransomeye/rebuild/ransomeye_ops/disaster_recovery/backup_manager.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Orchestrates encrypted backups of database, configuration, and artifacts with signed manifests

import os
import sys
import subprocess
import tarfile
import gzip
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization


class BackupManager:
    """Manages encrypted backups of RansomEye system."""
    
    def __init__(self, rebuild_root: str = None):
        self.rebuild_root = Path(rebuild_root) if rebuild_root else Path(
            os.environ.get('REBUILD_ROOT', '/home/ransomeye/rebuild')
        )
        self.backup_dir = self.rebuild_root / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Get encryption key path
        self.backup_pubkey_path = Path(os.environ.get(
            'OPS_BACKUP_PUBKEY_PATH',
            str(self.rebuild_root / 'certs' / 'backup_pubkey.pem')
        ))
        self.backup_passphrase = os.environ.get('OPS_BACKUP_PASSPHRASE', None)
        
        # DB credentials
        self.db_host = os.environ.get('DB_HOST', 'localhost')
        self.db_port = os.environ.get('DB_PORT', '5432')
        self.db_name = os.environ.get('DB_NAME', 'ransomeye')
        self.db_user = os.environ.get('DB_USER', 'gagan')
        self.db_pass = os.environ.get('DB_PASS', 'gagan')
    
    def _get_timestamp(self) -> str:
        """Get timestamp string for backup naming (offline-safe)."""
        return datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def backup_database(self, output_path: Path) -> bool:
        """Create PostgreSQL database dump."""
        try:
            # Set PGPASSWORD environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_pass
            
            # Run pg_dump
            cmd = [
                'pg_dump',
                '-h', self.db_host,
                '-p', self.db_port,
                '-U', self.db_user,
                '-d', self.db_name,
                '-F', 'c',  # Custom format
                '-f', str(output_path)
            ]
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"Database backup failed: {e.stderr}")
            return False
        except Exception as e:
            print(f"Database backup error: {e}")
            return False
    
    def backup_config(self, output_path: Path) -> bool:
        """Backup configuration files and keys."""
        try:
            with tarfile.open(str(output_path), 'w:gz') as tar:
                # Backup config directories from all modules
                config_dirs = [
                    self.rebuild_root / 'ransomeye_core' / 'config',
                    self.rebuild_root / 'ransomeye_install' / 'config',
                ]
                
                # Add all module configs
                for module_dir in self.rebuild_root.glob('ransomeye_*/config'):
                    if module_dir.exists() and module_dir.is_dir():
                        tar.add(str(module_dir), arcname=module_dir.name, recursive=True)
                
                # Backup certs
                certs_dir = self.rebuild_root / 'certs'
                if certs_dir.exists():
                    tar.add(str(certs_dir), arcname='certs', recursive=True)
                
                # Backup systemd files
                systemd_dir = self.rebuild_root / 'systemd'
                if systemd_dir.exists():
                    tar.add(str(systemd_dir), arcname='systemd', recursive=True)
                
                # Backup .env files (if they exist)
                for env_file in self.rebuild_root.rglob('.env'):
                    if env_file.is_file():
                        tar.add(str(env_file), arcname=f"env_files/{env_file.relative_to(self.rebuild_root)}")
            
            return True
        except Exception as e:
            print(f"Config backup failed: {e}")
            return False
    
    def backup_artifacts(self, output_path: Path) -> bool:
        """Backup forensic artifacts and evidence (incremental)."""
        try:
            with tarfile.open(str(output_path), 'w:gz') as tar:
                # Find forensic storage directories
                forensic_dirs = [
                    self.rebuild_root / 'ransomeye_forensic' / 'storage',
                    self.rebuild_root / 'ransomeye_killchain' / 'artifacts',
                ]
                
                for forensic_dir in forensic_dirs:
                    if forensic_dir.exists():
                        tar.add(str(forensic_dir), arcname=forensic_dir.name, recursive=True)
                
                # Backup logs (recent only, older logs should be archived separately)
                logs_dir = self.rebuild_root / 'logs'
                if logs_dir.exists():
                    # Only backup logs from last 7 days
                    cutoff_time = datetime.now().timestamp() - (7 * 24 * 60 * 60)
                    for log_file in logs_dir.rglob('*.log'):
                        if log_file.stat().st_mtime > cutoff_time:
                            tar.add(str(log_file), arcname=f"logs/{log_file.relative_to(logs_dir)}")
            
            return True
        except Exception as e:
            print(f"Artifacts backup failed: {e}")
            return False
    
    def _encrypt_file(self, input_path: Path, output_path: Path) -> bool:
        """Encrypt file using public key or passphrase."""
        try:
            with open(input_path, 'rb') as f:
                plaintext = f.read()
            
            if self.backup_pubkey_path.exists():
                # Use public key encryption (RSA-OAEP)
                with open(self.backup_pubkey_path, 'rb') as f:
                    public_key = serialization.load_pem_public_key(
                        f.read(),
                        backend=default_backend()
                    )
                
                # Encrypt with RSA-OAEP
                encrypted = public_key.encrypt(
                    plaintext,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None
                    )
                )
            elif self.backup_passphrase:
                # Use symmetric encryption (AES-GCM)
                key = hashlib.sha256(self.backup_passphrase.encode()).digest()
                aesgcm = AESGCM(key)
                nonce = os.urandom(12)
                encrypted = nonce + aesgcm.encrypt(nonce, plaintext, None)
            else:
                print("ERROR: No encryption key or passphrase provided")
                return False
            
            with open(output_path, 'wb') as f:
                f.write(encrypted)
            
            return True
        except Exception as e:
            print(f"Encryption failed: {e}")
            return False
    
    def _generate_manifest(self, backup_files: Dict[str, str], manifest_path: Path) -> bool:
        """Generate signed manifest of backup files."""
        try:
            manifest = {
                'timestamp': self._get_timestamp(),
                'version': '1.0',
                'files': {}
            }
            
            # Calculate checksums
            for file_type, file_path in backup_files.items():
                if Path(file_path).exists():
                    sha256 = hashlib.sha256()
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            sha256.update(chunk)
                    manifest['files'][file_type] = {
                        'path': file_path,
                        'sha256': sha256.hexdigest(),
                        'size': Path(file_path).stat().st_size
                    }
            
            # Write manifest
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            # Sign manifest (if signing key available)
            signing_key_path = self.rebuild_root / 'certs' / 'backup_signing_key.pem'
            if signing_key_path.exists():
                self._sign_manifest(manifest_path, signing_key_path)
            
            return True
        except Exception as e:
            print(f"Manifest generation failed: {e}")
            return False
    
    def _sign_manifest(self, manifest_path: Path, key_path: Path) -> None:
        """Sign manifest file."""
        try:
            with open(key_path, 'rb') as f:
                private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
            
            with open(manifest_path, 'rb') as f:
                manifest_data = f.read()
            
            signature = private_key.sign(
                manifest_data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            # Write signature
            sig_path = manifest_path.with_suffix('.sig')
            with open(sig_path, 'wb') as f:
                f.write(signature)
        except Exception as e:
            print(f"Manifest signing failed: {e}")
    
    def create_backup(self, include_artifacts: bool = True) -> Optional[Path]:
        """Create complete encrypted backup."""
        timestamp = self._get_timestamp()
        backup_name = f"ransomeye_backup_{timestamp}"
        temp_dir = self.backup_dir / f"temp_{timestamp}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            print(f"Creating backup: {backup_name}")
            
            # 1. Database backup
            print("  [1/4] Backing up database...")
            db_backup = temp_dir / "database.dump"
            if not self.backup_database(db_backup):
                return None
            
            # 2. Config backup
            print("  [2/4] Backing up configuration...")
            config_backup = temp_dir / "config.tar.gz"
            if not self.backup_config(config_backup):
                return None
            
            # 3. Artifacts backup (optional)
            artifacts_backup = None
            if include_artifacts:
                print("  [3/4] Backing up artifacts...")
                artifacts_backup = temp_dir / "artifacts.tar.gz"
                if not self.backup_artifacts(artifacts_backup):
                    print("  WARNING: Artifacts backup failed, continuing...")
            
            # 4. Create final tarball
            print("  [4/4] Creating final archive...")
            final_tarball = temp_dir / f"{backup_name}.tar.gz"
            with tarfile.open(str(final_tarball), 'w:gz') as tar:
                tar.add(str(db_backup), arcname='database.dump')
                tar.add(str(config_backup), arcname='config.tar.gz')
                if artifacts_backup and artifacts_backup.exists():
                    tar.add(str(artifacts_backup), arcname='artifacts.tar.gz')
            
            # 5. Encrypt
            print("  Encrypting backup...")
            encrypted_backup = self.backup_dir / f"{backup_name}.tar.gz.enc"
            if not self._encrypt_file(final_tarball, encrypted_backup):
                return None
            
            # 6. Generate manifest
            print("  Generating manifest...")
            manifest_path = self.backup_dir / f"{backup_name}.manifest.json"
            backup_files = {
                'database': str(db_backup),
                'config': str(config_backup),
                'encrypted_backup': str(encrypted_backup)
            }
            if artifacts_backup:
                backup_files['artifacts'] = str(artifacts_backup)
            
            self._generate_manifest(backup_files, manifest_path)
            
            # Cleanup temp files
            import shutil
            shutil.rmtree(temp_dir)
            
            print(f"Backup completed: {encrypted_backup}")
            return encrypted_backup
            
        except Exception as e:
            print(f"Backup creation failed: {e}")
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            return None


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Create encrypted backup of RansomEye system')
    parser.add_argument('--no-artifacts', action='store_true', help='Skip artifacts backup')
    parser.add_argument('--output-dir', type=str, help='Output directory for backups')
    
    args = parser.parse_args()
    
    manager = BackupManager()
    if args.output_dir:
        manager.backup_dir = Path(args.output_dir)
        manager.backup_dir.mkdir(parents=True, exist_ok=True)
    
    backup_path = manager.create_backup(include_artifacts=not args.no_artifacts)
    
    if backup_path:
        print(f"\n✓ Backup successful: {backup_path}")
        sys.exit(0)
    else:
        print("\n✗ Backup failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

