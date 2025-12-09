# Path and File Name : /home/ransomeye/rebuild/ransomeye_release_engineering/builder/artifact_signer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Signs release artifacts using RSA-4096 private key via GPG or OpenSSL

import subprocess
import sys
from pathlib import Path
from typing import List, Optional

# Project root
PROJECT_ROOT = Path("/home/ransomeye/rebuild")


class ArtifactSigner:
    """Signs release artifacts using RSA-4096."""
    
    def __init__(self, sign_key_path: Path):
        self.sign_key_path = Path(sign_key_path)
        if not self.sign_key_path.exists():
            raise FileNotFoundError(f"Signing key not found: {sign_key_path}")
    
    def _sign_with_gpg(self, artifact_path: Path) -> bool:
        """Sign artifact using GPG."""
        sig_path = Path(str(artifact_path) + ".sig")
        
        try:
            # Try GPG signing
            result = subprocess.run(
                [
                    "gpg",
                    "--detach-sign",
                    "--armor",
                    "--output", str(sig_path),
                    "--default-key", str(self.sign_key_path),
                    str(artifact_path)
                ],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0 and sig_path.exists():
                return True
            else:
                print(f"  ⚠️  GPG signing failed: {result.stderr}")
                return False
                
        except FileNotFoundError:
            return False  # GPG not available
        except subprocess.TimeoutExpired:
            print(f"  ⚠️  GPG signing timed out")
            return False
        except Exception as e:
            print(f"  ⚠️  GPG signing error: {e}")
            return False
    
    def _sign_with_openssl(self, artifact_path: Path) -> bool:
        """Sign artifact using OpenSSL."""
        sig_path = Path(str(artifact_path) + ".sig")
        
        try:
            # OpenSSL signing: openssl dgst -sha256 -sign key.pem -out file.sig file
            result = subprocess.run(
                [
                    "openssl", "dgst", "-sha256",
                    "-sign", str(self.sign_key_path),
                    "-out", str(sig_path),
                    str(artifact_path)
                ],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0 and sig_path.exists():
                return True
            else:
                print(f"  ⚠️  OpenSSL signing failed: {result.stderr}")
                return False
                
        except FileNotFoundError:
            return False  # OpenSSL not available
        except subprocess.TimeoutExpired:
            print(f"  ⚠️  OpenSSL signing timed out")
            return False
        except Exception as e:
            print(f"  ⚠️  OpenSSL signing error: {e}")
            return False
    
    def sign(self, artifact_path: Path) -> bool:
        """Sign a single artifact."""
        artifact_path = Path(artifact_path)
        if not artifact_path.exists():
            print(f"  ❌ Artifact not found: {artifact_path}")
            return False
        
        print(f"Signing: {artifact_path.name}")
        
        # Try GPG first, then OpenSSL
        if self._sign_with_gpg(artifact_path):
            print(f"  ✅ Signed with GPG: {artifact_path.name}.sig")
            return True
        elif self._sign_with_openssl(artifact_path):
            print(f"  ✅ Signed with OpenSSL: {artifact_path.name}.sig")
            return True
        else:
            print(f"  ❌ Failed to sign: {artifact_path.name}")
            return False
    
    def sign_all(self, artifact_paths: List[Path]) -> int:
        """Sign multiple artifacts."""
        signed_count = 0
        
        for artifact_path in artifact_paths:
            if self.sign(artifact_path):
                signed_count += 1
        
        return signed_count

