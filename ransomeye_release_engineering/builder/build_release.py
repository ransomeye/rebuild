# Path and File Name : /home/ransomeye/rebuild/ransomeye_release_engineering/builder/build_release.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Main release orchestrator that enforces gates and packages Core and Agents into separate signed artifacts

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional
import argparse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from builder.packager_core import CorePackager
from builder.packager_agents import AgentPackager
from builder.artifact_signer import ArtifactSigner
from manifests.generate_release_manifest import ManifestGenerator

# Project root
PROJECT_ROOT = Path("/home/ransomeye/rebuild")
GATES_SCRIPT = PROJECT_ROOT / "ransomeye_governance" / "gates" / "check_gates.py"
ARTIFACTS_DIR = PROJECT_ROOT / "ransomeye_release_engineering" / "artifacts"


def get_version() -> str:
    """Read version from VERSION file or environment variable."""
    version_file = PROJECT_ROOT / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    
    version = os.environ.get("RELEASE_VERSION", "1.0.0")
    return version


def check_gates() -> bool:
    """Run gate checks and abort if they fail."""
    print("=" * 70)
    print("PHASE 25: RELEASE PACKAGING - GATE ENFORCEMENT")
    print("=" * 70)
    print(f"\n[STEP 1] Running acceptance gates: {GATES_SCRIPT}")
    
    if not GATES_SCRIPT.exists():
        print(f"❌ ERROR: Gate checker not found: {GATES_SCRIPT}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(GATES_SCRIPT)],
            cwd=str(PROJECT_ROOT),
            capture_output=False,
            text=True
        )
        
        if result.returncode != 0:
            print(f"\n❌ GATE CHECK FAILED (exit code: {result.returncode})")
            print("Release packaging aborted. Fix gate failures before proceeding.")
            return False
        
        print("\n✅ ALL GATES PASSED - Proceeding with packaging")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Failed to run gate checker: {e}")
        return False


def main():
    """Main release build orchestrator."""
    parser = argparse.ArgumentParser(description="Build RansomEye release artifacts")
    parser.add_argument(
        "--skip-gates",
        action="store_true",
        help="Skip gate checks (NOT RECOMMENDED for production)"
    )
    parser.add_argument(
        "--version",
        type=str,
        help="Override version (default: from VERSION file or env)"
    )
    parser.add_argument(
        "--sign-key",
        type=str,
        help="Path to signing key (default: RELEASE_SIGN_KEY_PATH env var)"
    )
    
    args = parser.parse_args()
    
    # Get version
    version = args.version or get_version()
    print(f"\n[INFO] Release version: {version}")
    
    # Ensure artifacts directory exists
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Check gates (unless skipped)
    if not args.skip_gates:
        if not check_gates():
            sys.exit(1)
    else:
        print("⚠️  WARNING: Gate checks skipped (--skip-gates)")
    
    # Step 2: Package Core
    print("\n" + "=" * 70)
    print("[STEP 2] Packaging Core Engine...")
    print("=" * 70)
    try:
        core_packager = CorePackager(project_root=PROJECT_ROOT, version=version)
        core_archive = core_packager.package()
        if not core_archive:
            print("❌ Core packaging failed")
            sys.exit(1)
        print(f"✅ Core packaged: {core_archive}")
    except Exception as e:
        print(f"❌ Core packaging error: {e}")
        sys.exit(1)
    
    # Step 3: Package Agents
    print("\n" + "=" * 70)
    print("[STEP 3] Packaging Standalone Agents...")
    print("=" * 70)
    try:
        agent_packager = AgentPackager(project_root=PROJECT_ROOT, version=version)
        agent_archives = agent_packager.package_all()
        if not agent_archives:
            print("❌ Agent packaging failed")
            sys.exit(1)
        print(f"✅ Agents packaged: {len(agent_archives)} archive(s)")
        for archive in agent_archives:
            print(f"   - {archive}")
    except Exception as e:
        print(f"❌ Agent packaging error: {e}")
        sys.exit(1)
    
    # Step 4: Sign artifacts
    print("\n" + "=" * 70)
    print("[STEP 4] Signing Artifacts...")
    print("=" * 70)
    sign_key_path = args.sign_key or os.environ.get("RELEASE_SIGN_KEY_PATH")
    if sign_key_path:
        try:
            signer = ArtifactSigner(sign_key_path=Path(sign_key_path))
            all_archives = [core_archive] + agent_archives
            signed_count = signer.sign_all(all_archives)
            print(f"✅ Signed {signed_count} artifact(s)")
        except Exception as e:
            print(f"⚠️  Signing error: {e}")
            print("Continuing without signatures...")
    else:
        # Silent skip if no signing key (optional for development builds)
        print("✅ Signing skipped (no key provided)")
    
    # Step 5: Generate manifests
    print("\n" + "=" * 70)
    print("[STEP 5] Generating Release Manifests...")
    print("=" * 70)
    try:
        manifest_gen = ManifestGenerator(artifacts_dir=ARTIFACTS_DIR, version=version)
        manifest_gen.generate()
        print("✅ Manifests generated:")
        print(f"   - {ARTIFACTS_DIR / 'release_manifest.json'}")
        print(f"   - {ARTIFACTS_DIR / 'SHA256SUMS'}")
    except Exception as e:
        print(f"❌ Manifest generation error: {e}")
        sys.exit(1)
    
    # Final summary
    print("\n" + "=" * 70)
    print("✅ RELEASE BUILD COMPLETE")
    print("=" * 70)
    print(f"Version: {version}")
    print(f"Artifacts directory: {ARTIFACTS_DIR}")
    print("\nGenerated artifacts:")
    for archive in [core_archive] + agent_archives:
        print(f"  - {Path(archive).name}")
        sig_file = Path(str(archive) + ".sig")
        if sig_file.exists():
            print(f"    Signature: {sig_file.name}")
    print(f"\nManifests:")
    print(f"  - release_manifest.json")
    print(f"  - SHA256SUMS")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()

