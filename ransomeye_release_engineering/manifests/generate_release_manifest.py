# Path and File Name : /home/ransomeye/rebuild/ransomeye_release_engineering/manifests/generate_release_manifest.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Generates release_manifest.json and SHA256SUMS file for all release artifacts

import hashlib
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime

# Project root
PROJECT_ROOT = Path("/home/ransomeye/rebuild")


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


class ManifestGenerator:
    """Generates release manifests and SHA256 checksums."""
    
    def __init__(self, artifacts_dir: Path, version: str = "1.0.0"):
        self.artifacts_dir = Path(artifacts_dir)
        self.version = version
    
    def _find_artifacts(self) -> List[Path]:
        """Find all artifact files (excluding signatures and manifests)."""
        artifacts = []
        
        if not self.artifacts_dir.exists():
            return artifacts
        
        for item in self.artifacts_dir.iterdir():
            if item.is_file():
                # Exclude signature files and manifest files
                if not item.name.endswith('.sig') and \
                   item.name not in ['release_manifest.json', 'SHA256SUMS']:
                    artifacts.append(item)
        
        return sorted(artifacts)
    
    def generate(self) -> None:
        """Generate release_manifest.json and SHA256SUMS."""
        artifacts = self._find_artifacts()
        
        if not artifacts:
            print("⚠️  No artifacts found to generate manifest")
            return
        
        print(f"Generating manifests for {len(artifacts)} artifact(s)...")
        
        manifest_data = {
            "version": self.version,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "artifacts": []
        }
        
        sha256_lines = []
        
        for artifact_path in artifacts:
            print(f"  Processing: {artifact_path.name}")
            
            # Calculate SHA256
            sha256_hash = calculate_sha256(artifact_path)
            
            # Get file size
            file_size = artifact_path.stat().st_size
            
            # Check for signature
            sig_path = Path(str(artifact_path) + ".sig")
            has_signature = sig_path.exists()
            
            # Add to manifest
            manifest_data["artifacts"].append({
                "filename": artifact_path.name,
                "sha256": sha256_hash,
                "size_bytes": file_size,
                "size_mb": round(file_size / (1024 * 1024), 2),
                "signed": has_signature
            })
            
            # Add to SHA256SUMS
            sha256_lines.append(f"{sha256_hash}  {artifact_path.name}")
        
        # Write release_manifest.json
        manifest_path = self.artifacts_dir / "release_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest_data, f, indent=2)
        print(f"✅ Generated: {manifest_path.name}")
        
        # Write SHA256SUMS
        sha256sums_path = self.artifacts_dir / "SHA256SUMS"
        with open(sha256sums_path, 'w') as f:
            f.write('\n'.join(sha256_lines) + '\n')
        print(f"✅ Generated: {sha256sums_path.name}")
        
        print(f"\nManifest summary:")
        print(f"  - Total artifacts: {len(artifacts)}")
        print(f"  - Signed artifacts: {sum(1 for a in manifest_data['artifacts'] if a['signed'])}")
        print(f"  - Total size: {sum(a['size_mb'] for a in manifest_data['artifacts']):.2f} MB")

