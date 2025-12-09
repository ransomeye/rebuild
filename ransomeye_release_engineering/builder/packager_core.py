# Path and File Name : /home/ransomeye/rebuild/ransomeye_release_engineering/builder/packager_core.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Packages Core Engine components into tar.gz archive, excluding standalone agents

import tarfile
import gzip
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# Project root
PROJECT_ROOT = Path("/home/ransomeye/rebuild")
ARTIFACTS_DIR = PROJECT_ROOT / "ransomeye_release_engineering" / "artifacts"

# Core modules to include (only modules that actually exist)
CORE_MODULES = [
    "ransomeye_ai_core",
    "ransomeye_alert_engine",
    "ransomeye_db_core",
    "ransomeye_deception",
    "ransomeye_forensic",
    "ransomeye_hnmp_engine",
    "ransomeye_llm",
    "ransomeye_net_scanner",
    "ransomeye_response",
    "ransomeye_ui",
    "ransomeye_core",
    "ransomeye_install",
    "ransomeye_governance",
    "ransomeye_global_validator",
    "ransomeye_orchestrator",
    "ransomeye_correlation",
    "ransomeye_threat_intel",
    "ransomeye_killchain",
    "ransomeye_llm_behavior",
    "ransomeye_assistant",
    "ransomeye_assistant_advanced",
    "ransomeye_ai_advanced",
]

# Standalone agents to EXCLUDE
STANDALONE_AGENTS = [
    "ransomeye_linux_agent",
    "ransomeye_windows_agent",
    "ransomeye_dpi_probe",
]

# Additional root files to include
ROOT_FILES = [
    "install.sh",
    "uninstall.sh",
    "requirements.txt",
    "VERSION",
    "post_install_validator.py",
]

# Directories to include
ROOT_DIRS = [
    "systemd",
    "logs",
]


class CorePackager:
    """Packages Core Engine components into a tar.gz archive."""
    
    def __init__(self, project_root: Path = PROJECT_ROOT, version: str = "1.0.0"):
        self.project_root = project_root
        self.version = version
        self.artifacts_dir = ARTIFACTS_DIR
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    def _should_exclude(self, path: Path) -> bool:
        """Check if a path should be excluded from the archive."""
        # Exclude standalone agents
        for agent in STANDALONE_AGENTS:
            if agent in path.parts:
                return True
        
        # Exclude build artifacts
        if any(part in path.parts for part in ['__pycache__', '.pyc', '.pyo', '.pyd', '.git', '.pytest_cache', 'venv', '.venv']):
            return True
        
        # Exclude release engineering itself
        if 'ransomeye_release_engineering' in path.parts:
            return True
        
        return False
    
    def _get_all_files(self, base_path: Path, relative_to: Path) -> List[tuple]:
        """Recursively collect all files to include."""
        files = []
        
        if base_path.is_file():
            rel_path = base_path.relative_to(relative_to)
            if not self._should_exclude(base_path):
                files.append((base_path, rel_path))
        elif base_path.is_dir():
            try:
                for item in base_path.iterdir():
                    if not self._should_exclude(item):
                        files.extend(self._get_all_files(item, relative_to))
            except PermissionError:
                pass  # Skip directories we can't read
        
        return files
    
    def package(self) -> Optional[Path]:
        """Create the Core Engine tar.gz archive."""
        archive_name = f"ransomeye-core-{self.version}.tar.gz"
        archive_path = self.artifacts_dir / archive_name
        
        print(f"Creating Core archive: {archive_name}")
        print(f"Target: {archive_path}")
        
        # Remove existing archive if present
        if archive_path.exists():
            archive_path.unlink()
        
        all_files = []
        
        # Add core modules
        print("\nIncluding Core modules:")
        for module in CORE_MODULES:
            module_path = self.project_root / module
            if module_path.exists():
                print(f"  + {module}")
                module_files = self._get_all_files(module_path, self.project_root)
                all_files.extend(module_files)
            # Silently skip non-existent modules (they're not in the actual project)
        
        # Add root files (only include if they exist, silently skip missing optional ones)
        print("\nIncluding root files:")
        for root_file in ROOT_FILES:
            file_path = self.project_root / root_file
            if file_path.exists():
                print(f"  + {root_file}")
                all_files.append((file_path, Path(root_file)))
            # Silently skip missing files (they may be created in other phases)
        
        # Add root directories (only include if they exist)
        print("\nIncluding root directories:")
        for root_dir in ROOT_DIRS:
            dir_path = self.project_root / root_dir
            if dir_path.exists():
                print(f"  + {root_dir}/")
                dir_files = self._get_all_files(dir_path, self.project_root)
                all_files.extend(dir_files)
            # Silently skip missing directories (they may be created in other phases)
        
        if not all_files:
            print("❌ ERROR: No files to package")
            return None
        
        # Create tar.gz archive
        print(f"\nPackaging {len(all_files)} files into archive...")
        try:
            with tarfile.open(archive_path, "w:gz", compresslevel=6) as tar:
                for source_path, arcname in all_files:
                    try:
                        tar.add(source_path, arcname=arcname, recursive=False)
                    except Exception as e:
                        print(f"  ⚠️  Warning: Could not add {arcname}: {e}")
            
            archive_size = archive_path.stat().st_size
            size_mb = archive_size / (1024 * 1024)
            print(f"✅ Archive created: {archive_name} ({size_mb:.2f} MB)")
            
            return archive_path
            
        except Exception as e:
            print(f"❌ ERROR: Failed to create archive: {e}")
            return None

