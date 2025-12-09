# Path and File Name : /home/ransomeye/rebuild/ransomeye_release_engineering/validation/verify_release.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Verifies release bundle signatures and SHA256 hashes

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Project root
PROJECT_ROOT = Path("/home/ransomeye/rebuild")
ARTIFACTS_DIR = PROJECT_ROOT / "ransomeye_release_engineering" / "artifacts"


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


class ReleaseVerifier:
    """Verifies release artifacts signatures and checksums."""
    
    def __init__(self, artifacts_dir: Path = ARTIFACTS_DIR):
        self.artifacts_dir = Path(artifacts_dir)
    
    def verify_sha256sums(self) -> Tuple[bool, List[str]]:
        """Verify SHA256SUMS file against artifacts."""
        sha256sums_path = self.artifacts_dir / "SHA256SUMS"
        
        if not sha256sums_path.exists():
            return False, ["SHA256SUMS file not found"]
        
        errors = []
        verified_count = 0
        
        with open(sha256sums_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split()
                if len(parts) < 2:
                    continue
                
                expected_hash = parts[0]
                filename = parts[1]
                artifact_path = self.artifacts_dir / filename
                
                if not artifact_path.exists():
                    errors.append(f"Artifact not found: {filename}")
                    continue
                
                actual_hash = calculate_sha256(artifact_path)
                
                if actual_hash == expected_hash:
                    verified_count += 1
                    print(f"  ✅ {filename}: SHA256 verified")
                else:
                    errors.append(f"SHA256 mismatch for {filename}: expected {expected_hash[:16]}..., got {actual_hash[:16]}...")
        
        if errors:
            return False, errors
        
        print(f"✅ SHA256 verification: {verified_count} artifact(s) verified")
        return True, []
    
    def verify_signatures(self, public_key_path: Path = None) -> Tuple[bool, List[str]]:
        """Verify artifact signatures."""
        errors = []
        verified_count = 0
        
        # Find all artifacts
        artifacts = []
        for item in self.artifacts_dir.iterdir():
            if item.is_file() and not item.name.endswith('.sig') and \
               item.name not in ['release_manifest.json', 'SHA256SUMS']:
                artifacts.append(item)
        
        for artifact_path in artifacts:
            # Skip .keep and other non-artifact files
            if artifact_path.name == '.keep' or artifact_path.name.startswith('.'):
                continue
                
            sig_path = Path(str(artifact_path) + ".sig")
            
            if not sig_path.exists():
                # Only error if we have a public key (meaning signing was expected)
                if public_key_path:
                    errors.append(f"Signature not found for {artifact_path.name}")
                else:
                    # Without public key, just warn (signing may be optional)
                    print(f"  ⚠️  {artifact_path.name}: No signature (signing key not provided)")
                continue
            
            # Try GPG verification
            try:
                result = subprocess.run(
                    ["gpg", "--verify", str(sig_path), str(artifact_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    verified_count += 1
                    print(f"  ✅ {artifact_path.name}: GPG signature verified")
                    continue
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
            
            # Try OpenSSL verification
            if public_key_path and public_key_path.exists():
                try:
                    result = subprocess.run(
                        [
                            "openssl", "dgst", "-sha256",
                            "-verify", str(public_key_path),
                            "-signature", str(sig_path),
                            str(artifact_path)
                        ],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        verified_count += 1
                        print(f"  ✅ {artifact_path.name}: OpenSSL signature verified")
                        continue
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pass
            
            errors.append(f"Signature verification failed for {artifact_path.name}")
        
        if errors:
            return False, errors
        
        print(f"✅ Signature verification: {verified_count} artifact(s) verified")
        return True, []
    
    def verify_manifest(self) -> Tuple[bool, List[str]]:
        """Verify release_manifest.json structure and consistency."""
        manifest_path = self.artifacts_dir / "release_manifest.json"
        
        if not manifest_path.exists():
            return False, ["release_manifest.json not found"]
        
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON in manifest: {e}"]
        
        errors = []
        
        # Check required fields
        required_fields = ["version", "generated_at", "artifacts"]
        for field in required_fields:
            if field not in manifest:
                errors.append(f"Missing required field in manifest: {field}")
        
        if errors:
            return False, errors
        
        # Verify each artifact in manifest exists
        for artifact_info in manifest.get("artifacts", []):
            filename = artifact_info.get("filename")
            if not filename:
                errors.append("Artifact entry missing filename")
                continue
            
            artifact_path = self.artifacts_dir / filename
            if not artifact_path.exists():
                errors.append(f"Artifact in manifest not found: {filename}")
                continue
            
            # Verify SHA256 matches
            expected_hash = artifact_info.get("sha256")
            if expected_hash:
                actual_hash = calculate_sha256(artifact_path)
                if actual_hash != expected_hash:
                    errors.append(f"SHA256 mismatch in manifest for {filename}")
        
        if errors:
            return False, errors
        
        print(f"✅ Manifest verification: {len(manifest.get('artifacts', []))} artifact(s) validated")
        return True, []
    
    def verify_all(self, public_key_path: Path = None) -> bool:
        """Run all verification checks."""
        print("=" * 70)
        print("RELEASE ARTIFACT VERIFICATION")
        print("=" * 70)
        
        all_passed = True
        
        # Verify manifest
        print("\n[1] Verifying release_manifest.json...")
        passed, errors = self.verify_manifest()
        if not passed:
            all_passed = False
            for error in errors:
                print(f"  ❌ {error}")
        
        # Verify SHA256SUMS
        print("\n[2] Verifying SHA256SUMS...")
        passed, errors = self.verify_sha256sums()
        if not passed:
            all_passed = False
            for error in errors:
                print(f"  ❌ {error}")
        
        # Verify signatures
        print("\n[3] Verifying signatures...")
        passed, errors = self.verify_signatures(public_key_path)
        if not passed:
            all_passed = False
            for error in errors:
                print(f"  ❌ {error}")
        
        print("\n" + "=" * 70)
        if all_passed:
            print("✅ ALL VERIFICATIONS PASSED")
        else:
            print("❌ ONE OR MORE VERIFICATIONS FAILED")
        print("=" * 70)
        
        return all_passed


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify RansomEye release artifacts")
    parser.add_argument(
        "--artifacts-dir",
        type=str,
        default=str(ARTIFACTS_DIR),
        help="Path to artifacts directory"
    )
    parser.add_argument(
        "--public-key",
        type=str,
        help="Path to public key for signature verification"
    )
    
    args = parser.parse_args()
    
    verifier = ReleaseVerifier(artifacts_dir=Path(args.artifacts_dir))
    public_key = Path(args.public_key) if args.public_key else None
    
    success = verifier.verify_all(public_key_path=public_key)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

