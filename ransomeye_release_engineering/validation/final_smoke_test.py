# Path and File Name : /home/ransomeye/rebuild/ransomeye_release_engineering/validation/final_smoke_test.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Unpacks Core artifact in temp directory to verify folder structure and key components

import tarfile
import tempfile
import shutil
import zipfile
from pathlib import Path
from typing import List, Tuple

# Project root
PROJECT_ROOT = Path("/home/ransomeye/rebuild")
ARTIFACTS_DIR = PROJECT_ROOT / "ransomeye_release_engineering" / "artifacts"


class SmokeTester:
    """Performs smoke test on release artifacts."""
    
    def __init__(self, artifacts_dir: Path = ARTIFACTS_DIR):
        self.artifacts_dir = Path(artifacts_dir)
    
    def test_core_archive(self, archive_path: Path) -> Tuple[bool, List[str]]:
        """Test Core archive by unpacking and verifying structure."""
        errors = []
        warnings = []
        
        print(f"\nTesting Core archive: {archive_path.name}")
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            extract_path = temp_path / "extracted"
            extract_path.mkdir()
            
            try:
                # Extract archive
                print(f"  Extracting to: {extract_path}")
                with tarfile.open(archive_path, "r:gz") as tar:
                    # Use filter='data' to avoid deprecation warning in Python 3.14+
                    if hasattr(tarfile, 'data_filter'):
                        tar.extractall(extract_path, filter='data')
                    else:
                        tar.extractall(extract_path)
                
                # Verify key directories exist
                required_dirs = [
                    "ransomeye_install",
                    "ransomeye_core",
                    "ransomeye_ai_core",
                    "ransomeye_db_core",
                    "ransomeye_alert_engine",
                    "systemd"
                ]
                
                print("\n  Verifying required directories:")
                for req_dir in required_dirs:
                    dir_path = extract_path / req_dir
                    if dir_path.exists():
                        print(f"    ✅ {req_dir}/")
                    else:
                        errors.append(f"Required directory missing: {req_dir}")
                        print(f"    ❌ {req_dir}/ (MISSING)")
                
                # Verify key files (some may be optional)
                required_files = [
                    ("VERSION", True),  # Required
                ]
                optional_files = [
                    ("install.sh", False),
                    ("requirements.txt", False),
                    ("uninstall.sh", False),
                ]
                
                print("\n  Verifying required files:")
                for req_file, is_required in required_files:
                    file_path = extract_path / req_file
                    if file_path.exists():
                        print(f"    ✅ {req_file}")
                    else:
                        if is_required:
                            errors.append(f"Required file missing: {req_file}")
                            print(f"    ❌ {req_file} (MISSING)")
                        else:
                            print(f"    ⚠️  {req_file} (optional, not found)")
                
                # Only show optional files section if at least one exists
                optional_found = any((extract_path / opt_file).exists() for opt_file, _ in optional_files)
                if optional_found:
                    print("\n  Checking optional files:")
                    for opt_file, _ in optional_files:
                        file_path = extract_path / opt_file
                        if file_path.exists():
                            print(f"    ✅ {opt_file}")
                        # Silently skip missing optional files
                
                # Verify standalone agents are NOT included
                excluded_agents = [
                    "ransomeye_linux_agent",
                    "ransomeye_windows_agent",
                    "ransomeye_dpi_probe"
                ]
                
                print("\n  Verifying standalone agents are excluded:")
                for agent in excluded_agents:
                    agent_path = extract_path / agent
                    if agent_path.exists():
                        errors.append(f"Standalone agent should not be in Core: {agent}")
                        print(f"    ❌ {agent}/ (SHOULD NOT BE PRESENT)")
                    else:
                        print(f"    ✅ {agent}/ (correctly excluded)")
                
                # Check for systemd service files
                systemd_path = extract_path / "systemd"
                if systemd_path.exists():
                    service_files = list(systemd_path.glob("*.service"))
                    print(f"\n  Found {len(service_files)} systemd service file(s)")
                    if len(service_files) == 0:
                        warnings.append("No systemd service files found")
                
            except tarfile.TarError as e:
                errors.append(f"Failed to extract archive: {e}")
            except Exception as e:
                errors.append(f"Unexpected error: {e}")
        
        if errors:
            return False, errors
        
        if warnings:
            print("\n  ⚠️  Warnings:")
            for warning in warnings:
                print(f"    - {warning}")
        
        print("\n  ✅ Core archive structure verified")
        return True, []
    
    def test_agent_archive(self, archive_path: Path, agent_type: str) -> Tuple[bool, List[str]]:
        """Test agent archive by unpacking and verifying structure."""
        errors = []
        
        print(f"\nTesting {agent_type} archive: {archive_path.name}")
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            extract_path = temp_path / "extracted"
            extract_path.mkdir()
            
            try:
                # Extract archive (tar.gz or zip)
                print(f"  Extracting to: {extract_path}")
                if archive_path.suffix == '.gz' or archive_path.suffixes == ['.tar', '.gz']:
                    with tarfile.open(archive_path, "r:gz") as tar:
                        # Use filter='data' to avoid deprecation warning in Python 3.14+
                        if hasattr(tarfile, 'data_filter'):
                            tar.extractall(extract_path, filter='data')
                        else:
                            tar.extractall(extract_path)
                elif archive_path.suffix == '.zip':
                    with zipfile.ZipFile(archive_path, 'r') as zipf:
                        zipf.extractall(extract_path)
                else:
                    errors.append(f"Unsupported archive format: {archive_path.suffix}")
                    return False, errors
                
                # Verify agent directory exists
                agent_dir_name = f"ransomeye_{agent_type.replace(' ', '_')}"
                agent_path = extract_path / agent_dir_name
                
                if agent_path.exists():
                    print(f"    ✅ {agent_dir_name}/")
                else:
                    # Try alternative naming
                    found = False
                    for item in extract_path.iterdir():
                        if 'agent' in item.name.lower() or 'probe' in item.name.lower():
                            agent_path = item
                            found = True
                            break
                    
                    if not found:
                        errors.append(f"Agent directory not found: {agent_dir_name}")
                        print(f"    ❌ {agent_dir_name}/ (MISSING)")
                
                # Verify key subdirectories
                if agent_path.exists():
                    required_subdirs = ["engine", "transport"]
                    print("\n  Verifying agent subdirectories:")
                    for subdir in required_subdirs:
                        subdir_path = agent_path / subdir
                        if subdir_path.exists():
                            print(f"    ✅ {subdir}/")
                        else:
                            print(f"    ⚠️  {subdir}/ (not found)")
                
            except Exception as e:
                errors.append(f"Failed to extract or verify archive: {e}")
        
        if errors:
            return False, errors
        
        print(f"\n  ✅ {agent_type} archive structure verified")
        return True, []
    
    def run_all_tests(self) -> bool:
        """Run smoke tests on all artifacts."""
        print("=" * 70)
        print("RELEASE ARTIFACT SMOKE TESTS")
        print("=" * 70)
        
        all_passed = True
        
        # Find Core archive
        core_archives = list(self.artifacts_dir.glob("ransomeye-core-*.tar.gz"))
        if core_archives:
            passed, errors = self.test_core_archive(core_archives[0])
            if not passed:
                all_passed = False
                for error in errors:
                    print(f"  ❌ {error}")
        else:
            print("\n⚠️  No Core archive found for testing")
        
        # Find agent archives
        linux_archives = list(self.artifacts_dir.glob("ransomeye-linux-agent-*.tar.gz"))
        if linux_archives:
            passed, errors = self.test_agent_archive(linux_archives[0], "linux_agent")
            if not passed:
                all_passed = False
        
        windows_archives = list(self.artifacts_dir.glob("ransomeye-windows-agent-*.zip"))
        if windows_archives:
            passed, errors = self.test_agent_archive(windows_archives[0], "windows_agent")
            if not passed:
                all_passed = False
        
        probe_archives = list(self.artifacts_dir.glob("ransomeye-dpi-probe-*.tar.gz"))
        if probe_archives:
            passed, errors = self.test_agent_archive(probe_archives[0], "dpi_probe")
            if not passed:
                all_passed = False
        
        print("\n" + "=" * 70)
        if all_passed:
            print("✅ ALL SMOKE TESTS PASSED")
        else:
            print("❌ ONE OR MORE SMOKE TESTS FAILED")
        print("=" * 70)
        
        return all_passed


def main():
    """Main entry point."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Run smoke tests on release artifacts")
    parser.add_argument(
        "--artifacts-dir",
        type=str,
        default=str(ARTIFACTS_DIR),
        help="Path to artifacts directory"
    )
    
    args = parser.parse_args()
    
    tester = SmokeTester(artifacts_dir=Path(args.artifacts_dir))
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

