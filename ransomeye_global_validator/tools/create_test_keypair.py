# Path and File Name : /home/ransomeye/rebuild/ransomeye_global_validator/tools/create_test_keypair.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Generates ephemeral RSA keypair for CI tests and development

import os
import sys
from pathlib import Path
from Crypto.PublicKey import RSA

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def create_keypair(key_dir: str = None):
    """
    Create RSA keypair for signing.
    
    Args:
        key_dir: Directory to save keys (default: validator keys directory)
    """
    if key_dir is None:
        key_dir = os.environ.get(
            'VALIDATOR_KEYS_DIR',
            '/home/ransomeye/rebuild/ransomeye_global_validator/keys'
        )
    
    key_path = Path(key_dir)
    key_path.mkdir(parents=True, exist_ok=True)
    
    # Generate 2048-bit RSA key
    key = RSA.generate(2048)
    
    # Save private key
    private_key_path = key_path / 'sign_key.pem'
    with open(private_key_path, 'wb') as f:
        f.write(key.export_key(format='PEM'))
    print(f"Private key saved to: {private_key_path}")
    os.chmod(private_key_path, 0o600)  # Restrict permissions
    
    # Save public key
    public_key_path = key_path / 'sign_key.pub'
    with open(public_key_path, 'wb') as f:
        f.write(key.publickey().export_key(format='PEM'))
    print(f"Public key saved to: {public_key_path}")
    
    print("Keypair created successfully")


if __name__ == "__main__":
    create_keypair()

