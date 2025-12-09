# Path and File Name : /home/ransomeye/rebuild/ransomeye_ops/disaster_recovery/restore_manager.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Restores system from encrypted backup bundle with service management

import os
import sys
import subprocess
import tarfile
import json
import shutil
from pathlib import Path
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend


class RestoreManager:
    """Manages restoration from encrypted backups."""
    
    def __init__(self, rebuild_root: str = None):
        self.rebuild_root = Path(rebuild_root) if rebuild_root else Path(
            os.environ.get('REBUILD_ROOT', '/home/ransomeye/rebuild')
        )
        
        # Get decryption key
        self.backup_privkey_path = Path(os.environ.get(
            'OPS_BACKUP_PRIVKEY_PATH',
            str(self.rebuild_root / 'certs' / 'backup_privkey.pem')
        ))
        self.backup_passphrase = os.environ.get('OPS_BACKUP_PASSPHRASE', None)
        
        # DB credentials
        self.db_host = os.environ.get('DB_HOST', 'localhost')
        self.db_port = os.environ.get('DB_PORT', '5432')
        self.db_name = os.environ.get('DB_NAME', 'ransomeye')
        self.db_user = os.environ.get('DB_USER', 'gagan')
        self.db_pass = os.environ.get('DB_PASS', 'gagan')
    
    def _decrypt_file(self, encrypted_path: Path, output_path: Path) -> bool:
        """Decrypt encrypted backup file."""
        try:
            with open(encrypted_path, 'rb') as f:
                encrypted_data = f.read()
            
            if self.backup_privkey_path.exists():
                # Use private key decryption
                with open(self.backup_privkey_path, 'rb') as f:
                    private_key = serialization.load_pem_private_key(
                        f.read(),
                        password=None,
                        backend=default_backend()
                    )
                
                plaintext = private_key.decrypt(
                    encrypted_data,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None
                    )
                )
            elif self.backup_passphrase:
                # Use symmetric decryption
                key = hashlib.sha256(self.backup_passphrase.encode()).digest()
                aesgcm = AESGCM(key)
                nonce = encrypted_data[:12]
                ciphertext = encrypted_data[12:]
                plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            else:
                print("ERROR: No decryption key or passphrase provided")
                return False
            
            with open(output_path, 'wb') as f:
                f.write(plaintext)
            
            return True
        except Exception as e:
            print(f"Decryption failed: {e}")
            return False
    
    def _stop_services(self) -> bool:
        """Stop all RansomEye services."""
        try:
            print("Stopping RansomEye services...")
            services = [
                'ransomeye-core.service',
                'ransomeye-ai-core.service',
                'ransomeye-alert-engine.service',
                'ransomeye-db-core.service',
            ]
            
            for service in services:
                try:
                    subprocess.run(
                        ['systemctl', 'stop', service],
                        check=False,
                        capture_output=True
                    )
                except Exception:
                    pass  # Service may not exist
            
            return True
        except Exception as e:
            print(f"Error stopping services: {e}")
            return False
    
    def _start_services(self) -> bool:
        """Start all RansomEye services."""
        try:
            print("Starting RansomEye services...")
            services = [
                'ransomeye-core.service',
                'ransomeye-db-core.service',
                'ransomeye-ai-core.service',
                'ransomeye-alert-engine.service',
            ]
            
            for service in services:
                try:
                    subprocess.run(
                        ['systemctl', 'start', service],
                        check=False,
                        capture_output=True
                    )
                except Exception:
                    pass
            
            return True
        except Exception as e:
            print(f"Error starting services: {e}")
            return False
    
    def restore_database(self, dump_path: Path) -> bool:
        """Restore PostgreSQL database from dump."""
        try:
            print("Restoring database...")
            
            # Drop existing database (if needed)
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_pass
            
            # Create database if it doesn't exist
            subprocess.run(
                ['psql', '-h', self.db_host, '-p', self.db_port, '-U', self.db_user, '-d', 'postgres',
                 '-c', f'CREATE DATABASE {self.db_name};'],
                env=env,
                check=False,
                capture_output=True
            )
            
            # Restore from dump
            cmd = [
                'pg_restore',
                '-h', self.db_host,
                '-p', self.db_port,
                '-U', self.db_user,
                '-d', self.db_name,
                '-c',  # Clean (drop) before restore
                str(dump_path)
            ]
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            
            print("Database restored successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Database restore failed: {e.stderr}")
            return False
        except Exception as e:
            print(f"Database restore error: {e}")
            return False
    
    def restore_config(self, config_archive: Path) -> bool:
        """Restore configuration files."""
        try:
            print("Restoring configuration...")
            
            with tarfile.open(str(config_archive), 'r:gz') as tar:
                # Extract to temporary location first
                temp_dir = self.rebuild_root / 'restore_temp'
                temp_dir.mkdir(exist_ok=True)
                tar.extractall(path=temp_dir)
                
                # Move files to correct locations
                for item in temp_dir.rglob('*'):
                    if item.is_file():
                        rel_path = item.relative_to(temp_dir)
                        target = self.rebuild_root / rel_path
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(item), str(target))
                
                # Cleanup
                shutil.rmtree(temp_dir)
            
            print("Configuration restored successfully")
            return True
        except Exception as e:
            print(f"Config restore failed: {e}")
            return False
    
    def restore_artifacts(self, artifacts_archive: Path) -> bool:
        """Restore forensic artifacts."""
        try:
            print("Restoring artifacts...")
            
            with tarfile.open(str(artifacts_archive), 'r:gz') as tar:
                tar.extractall(path=self.rebuild_root)
            
            print("Artifacts restored successfully")
            return True
        except Exception as e:
            print(f"Artifacts restore failed: {e}")
            return False
    
    def restore_from_backup(self, backup_path: Path, verify: bool = True) -> bool:
        """Restore system from encrypted backup."""
        import tempfile
        
        if not backup_path.exists():
            print(f"ERROR: Backup file not found: {backup_path}")
            return False
        
        if verify:
            # Verify backup integrity first
            from .verify_backup import BackupVerifier
            verifier = BackupVerifier(self.rebuild_root)
            if not verifier.verify_backup(backup_path):
                print("ERROR: Backup verification failed")
                return False
        
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            print(f"Restoring from backup: {backup_path}")
            
            # 1. Decrypt backup
            print("  [1/5] Decrypting backup...")
            decrypted_backup = temp_dir / "backup.tar.gz"
            if not self._decrypt_file(backup_path, decrypted_backup):
                return False
            
            # 2. Extract tarball
            print("  [2/5] Extracting backup...")
            extract_dir = temp_dir / "extracted"
            extract_dir.mkdir()
            with tarfile.open(str(decrypted_backup), 'r:gz') as tar:
                tar.extractall(path=extract_dir)
            
            # 3. Stop services
            print("  [3/5] Stopping services...")
            if not self._stop_services():
                print("  WARNING: Some services may not have stopped")
            
            # 4. Restore components
            print("  [4/5] Restoring components...")
            
            # Database
            db_dump = extract_dir / "database.dump"
            if db_dump.exists():
                if not self.restore_database(db_dump):
                    return False
            
            # Config
            config_archive = extract_dir / "config.tar.gz"
            if config_archive.exists():
                if not self.restore_config(config_archive):
                    return False
            
            # Artifacts
            artifacts_archive = extract_dir / "artifacts.tar.gz"
            if artifacts_archive.exists():
                if not self.restore_artifacts(artifacts_archive):
                    print("  WARNING: Artifacts restore failed")
            
            # 5. Start services
            print("  [5/5] Starting services...")
            if not self._start_services():
                print("  WARNING: Some services may not have started")
            
            # Cleanup
            shutil.rmtree(temp_dir)
            
            print("\n✓ Restore completed successfully")
            return True
            
        except Exception as e:
            print(f"\n✗ Restore failed: {e}")
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Restore RansomEye system from encrypted backup')
    parser.add_argument('backup_path', type=str, help='Path to encrypted backup file')
    parser.add_argument('--no-verify', action='store_true', help='Skip backup verification')
    
    args = parser.parse_args()
    
    manager = RestoreManager()
    success = manager.restore_from_backup(Path(args.backup_path), verify=not args.no_verify)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

