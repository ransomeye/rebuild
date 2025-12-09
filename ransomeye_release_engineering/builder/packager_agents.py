# Path and File Name : /home/ransomeye/rebuild/ransomeye_release_engineering/builder/packager_agents.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Packages standalone Linux Agent, Windows Agent, and DPI Probe into separate archives

import tarfile
import zipfile
from pathlib import Path
from typing import List, Optional
import os

# Project root
PROJECT_ROOT = Path("/home/ransomeye/rebuild")
ARTIFACTS_DIR = PROJECT_ROOT / "ransomeye_release_engineering" / "artifacts"


class AgentPackager:
    """Packages standalone agents into separate archives."""
    
    def __init__(self, project_root: Path = PROJECT_ROOT, version: str = "1.0.0"):
        self.project_root = project_root
        self.version = version
        self.artifacts_dir = ARTIFACTS_DIR
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    def _should_exclude(self, path: Path) -> bool:
        """Check if a path should be excluded from the archive."""
        # Exclude build artifacts
        if any(part in path.parts for part in ['__pycache__', '.pyc', '.pyo', '.pyd', '.git', '.pytest_cache', 'venv', '.venv']):
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
    
    def package_linux_agent(self) -> Optional[Path]:
        """Package Linux Agent into tar.gz archive."""
        agent_dir = self.project_root / "ransomeye_linux_agent"
        if not agent_dir.exists():
            print("❌ ERROR: Linux Agent directory not found")
            return None
        
        archive_name = f"ransomeye-linux-agent-{self.version}.tar.gz"
        archive_path = self.artifacts_dir / archive_name
        
        print(f"\nPackaging Linux Agent: {archive_name}")
        
        # Remove existing archive if present
        if archive_path.exists():
            archive_path.unlink()
        
        # Collect all files
        all_files = self._get_all_files(agent_dir, self.project_root)
        
        # Also include install.sh if it exists in the agent directory
        agent_install = agent_dir / "install.sh"
        if agent_install.exists():
            rel_path = Path("ransomeye_linux_agent") / "install.sh"
            all_files.append((agent_install, rel_path))
        
        if not all_files:
            print("❌ ERROR: No files to package")
            return None
        
        # Create tar.gz archive
        print(f"Packaging {len(all_files)} files...")
        try:
            with tarfile.open(archive_path, "w:gz", compresslevel=6) as tar:
                for source_path, arcname in all_files:
                    try:
                        tar.add(source_path, arcname=arcname, recursive=False)
                    except Exception as e:
                        print(f"  ⚠️  Warning: Could not add {arcname}: {e}")
            
            archive_size = archive_path.stat().st_size
            size_mb = archive_size / (1024 * 1024)
            print(f"✅ Linux Agent packaged: {archive_name} ({size_mb:.2f} MB)")
            
            return archive_path
            
        except Exception as e:
            print(f"❌ ERROR: Failed to create archive: {e}")
            return None
    
    def package_windows_agent(self) -> Optional[Path]:
        """Package Windows Agent into zip archive."""
        agent_dir = self.project_root / "ransomeye_windows_agent"
        if not agent_dir.exists():
            print("❌ ERROR: Windows Agent directory not found")
            return None
        
        archive_name = f"ransomeye-windows-agent-{self.version}.zip"
        archive_path = self.artifacts_dir / archive_name
        
        print(f"\nPackaging Windows Agent: {archive_name}")
        
        # Remove existing archive if present
        if archive_path.exists():
            archive_path.unlink()
        
        # Collect all files
        all_files = self._get_all_files(agent_dir, self.project_root)
        
        # Also include installer if it exists
        installer_dir = agent_dir / "installer"
        if installer_dir.exists():
            installer_files = self._get_all_files(installer_dir, self.project_root)
            all_files.extend(installer_files)
        
        if not all_files:
            print("❌ ERROR: No files to package")
            return None
        
        # Create zip archive
        print(f"Packaging {len(all_files)} files...")
        try:
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                for source_path, arcname in all_files:
                    try:
                        zipf.write(source_path, arcname=arcname)
                    except Exception as e:
                        print(f"  ⚠️  Warning: Could not add {arcname}: {e}")
            
            archive_size = archive_path.stat().st_size
            size_mb = archive_size / (1024 * 1024)
            print(f"✅ Windows Agent packaged: {archive_name} ({size_mb:.2f} MB)")
            
            return archive_path
            
        except Exception as e:
            print(f"❌ ERROR: Failed to create archive: {e}")
            return None
    
    def package_dpi_probe(self) -> Optional[Path]:
        """Package DPI Probe into tar.gz archive."""
        probe_dir = self.project_root / "ransomeye_dpi_probe"
        if not probe_dir.exists():
            print("❌ ERROR: DPI Probe directory not found")
            return None
        
        archive_name = f"ransomeye-dpi-probe-{self.version}.tar.gz"
        archive_path = self.artifacts_dir / archive_name
        
        print(f"\nPackaging DPI Probe: {archive_name}")
        
        # Remove existing archive if present
        if archive_path.exists():
            archive_path.unlink()
        
        # Collect all files
        all_files = self._get_all_files(probe_dir, self.project_root)
        
        if not all_files:
            print("❌ ERROR: No files to package")
            return None
        
        # Create tar.gz archive
        print(f"Packaging {len(all_files)} files...")
        try:
            with tarfile.open(archive_path, "w:gz", compresslevel=6) as tar:
                for source_path, arcname in all_files:
                    try:
                        tar.add(source_path, arcname=arcname, recursive=False)
                    except Exception as e:
                        print(f"  ⚠️  Warning: Could not add {arcname}: {e}")
            
            archive_size = archive_path.stat().st_size
            size_mb = archive_size / (1024 * 1024)
            print(f"✅ DPI Probe packaged: {archive_name} ({size_mb:.2f} MB)")
            
            return archive_path
            
        except Exception as e:
            print(f"❌ ERROR: Failed to create archive: {e}")
            return None
    
    def package_all(self) -> List[Path]:
        """Package all standalone agents."""
        archives = []
        
        linux_archive = self.package_linux_agent()
        if linux_archive:
            archives.append(linux_archive)
        
        windows_archive = self.package_windows_agent()
        if windows_archive:
            archives.append(windows_archive)
        
        probe_archive = self.package_dpi_probe()
        if probe_archive:
            archives.append(probe_archive)
        
        return archives

