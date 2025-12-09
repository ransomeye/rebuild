# Path and File Name : /home/ransomeye/rebuild/ransomeye_ops/key_management/rotate_db_creds.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Rotates PostgreSQL user password and updates .env files, restarts services

import os
import sys
import subprocess
import secrets
import re
from pathlib import Path
from typing import List, Optional


class DBCredentialRotator:
    """Rotates database credentials."""
    
    def __init__(self, rebuild_root: str = None):
        self.rebuild_root = Path(rebuild_root) if rebuild_root else Path(
            os.environ.get('REBUILD_ROOT', '/home/ransomeye/rebuild')
        )
        
        self.db_host = os.environ.get('DB_HOST', 'localhost')
        self.db_port = os.environ.get('DB_PORT', '5432')
        self.db_name = os.environ.get('DB_NAME', 'ransomeye')
        self.db_user = os.environ.get('DB_USER', 'gagan')
        self.current_db_pass = os.environ.get('DB_PASS', 'gagan')
    
    def generate_password(self, length: int = 32) -> str:
        """Generate secure random password."""
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def update_postgres_password(self, new_password: str) -> bool:
        """Update PostgreSQL user password."""
        try:
            print(f"Updating PostgreSQL password for user '{self.db_user}'...")
            
            env = os.environ.copy()
            env['PGPASSWORD'] = self.current_db_pass
            
            # Use psql to change password
            cmd = [
                'psql',
                '-h', self.db_host,
                '-p', self.db_port,
                '-U', self.db_user,
                '-d', 'postgres',
                '-c', f"ALTER USER {self.db_user} WITH PASSWORD '{new_password}';"
            ]
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            
            print("✓ PostgreSQL password updated")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to update PostgreSQL password: {e.stderr}")
            return False
        except Exception as e:
            print(f"✗ Error updating password: {e}")
            return False
    
    def find_env_files(self) -> List[Path]:
        """Find all .env files in the project."""
        env_files = []
        
        # Search for .env files
        for env_file in self.rebuild_root.rglob('.env'):
            if env_file.is_file():
                env_files.append(env_file)
        
        # Also check for sample.env files that might need updating
        for sample_file in self.rebuild_root.rglob('sample.env'):
            if sample_file.is_file():
                env_files.append(sample_file)
        
        return env_files
    
    def update_env_file(self, env_file: Path, new_password: str) -> bool:
        """Update DB_PASS in .env file."""
        try:
            with open(env_file, 'r') as f:
                content = f.read()
            
            # Replace DB_PASS line
            pattern = r'^DB_PASS\s*=\s*.*$'
            replacement = f'DB_PASS={new_password}'
            
            new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            
            # If no DB_PASS found, add it
            if new_content == content and 'DB_PASS' not in content:
                new_content += f'\nDB_PASS={new_password}\n'
            
            with open(env_file, 'w') as f:
                f.write(new_content)
            
            return True
            
        except Exception as e:
            print(f"Error updating {env_file}: {e}")
            return False
    
    def restart_services(self) -> bool:
        """Restart RansomEye services to pick up new credentials."""
        try:
            print("Restarting services...")
            
            services = [
                'ransomeye-core.service',
                'ransomeye-db-core.service',
                'ransomeye-ai-core.service',
                'ransomeye-alert-engine.service',
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
                    pass  # Service may not exist
            
            print("✓ Services restarted")
            return True
            
        except Exception as e:
            print(f"WARNING: Service restart had issues: {e}")
            return True  # Not critical
    
    def rotate_credentials(self, new_password: Optional[str] = None) -> bool:
        """Rotate database credentials."""
        try:
            if new_password is None:
                new_password = self.generate_password()
            
            print(f"Rotating database credentials for user '{self.db_user}'...")
            print(f"New password length: {len(new_password)}")
            
            # Step 1: Update PostgreSQL
            if not self.update_postgres_password(new_password):
                return False
            
            # Step 2: Update .env files
            print("Updating .env files...")
            env_files = self.find_env_files()
            updated_count = 0
            
            for env_file in env_files:
                if self.update_env_file(env_file, new_password):
                    updated_count += 1
                    print(f"  ✓ Updated: {env_file.relative_to(self.rebuild_root)}")
            
            print(f"✓ Updated {updated_count} environment file(s)")
            
            # Step 3: Restart services
            self.restart_services()
            
            print("\n✓ Credential rotation completed successfully")
            print(f"New password: {new_password}")
            print("WARNING: Save this password securely!")
            
            return True
            
        except Exception as e:
            print(f"\n✗ Credential rotation failed: {e}")
            return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Rotate database credentials')
    parser.add_argument('--password', type=str, help='New password (if not provided, generates random)')
    
    args = parser.parse_args()
    
    rotator = DBCredentialRotator()
    success = rotator.rotate_credentials(new_password=args.password)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

