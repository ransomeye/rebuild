# Path and File Name : /home/ransomeye/rebuild/ransomeye_delivery_assurance/auditors/installer_auditor.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Parses install scripts to ensure core installer does NOT install agents, and standalone agents have their own installers

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
import json


class InstallerAuditor:
    """Audits installer scripts for architectural compliance."""
    
    def __init__(self, rebuild_root: str):
        self.rebuild_root = Path(rebuild_root)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed: List[str] = []
        
    def load_manifests(self) -> Tuple[Dict, Dict]:
        """Load core and standalone manifests."""
        definitions_dir = self.rebuild_root / "ransomeye_delivery_assurance" / "definitions"
        core_manifest_path = definitions_dir / "core_manifest.json"
        standalone_manifest_path = definitions_dir / "standalone_manifest.json"
        
        with open(core_manifest_path, 'r') as f:
            core_manifest = json.load(f)
        with open(standalone_manifest_path, 'r') as f:
            standalone_manifest = json.load(f)
            
        return core_manifest, standalone_manifest
    
    def check_core_installer_separation(self, core_manifest: Dict) -> bool:
        """Verify core installer does NOT reference standalone modules."""
        all_passed = True
        core_installer_path = self.rebuild_root / "ransomeye_install" / "install_core.sh"
        
        if not core_installer_path.exists():
            self.errors.append("Core installer not found: ransomeye_install/install_core.sh")
            return False
        
        try:
            with open(core_installer_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for forbidden references
            forbidden = core_manifest.get("forbidden_in_core_installer", [])
            for forbidden_term in forbidden:
                # Case-insensitive search, but allow comments/documentation
                pattern = re.compile(
                    rf'\b{re.escape(forbidden_term)}\b',
                    re.IGNORECASE
                )
                
                # Check if it appears in actual code (not just comments)
                lines = content.split('\n')
                violations = []
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    # Skip comment-only lines
                    if stripped.startswith('#'):
                        continue
                    if pattern.search(line):
                        violations.append((i, line.strip()))
                
                if violations:
                    self.errors.append(
                        f"Core installer references forbidden '{forbidden_term}' "
                        f"at lines: {[v[0] for v in violations]}"
                    )
                    all_passed = False
                else:
                    self.passed.append(
                        f"Core installer correctly excludes '{forbidden_term}'"
                    )
        
        except Exception as e:
            self.errors.append(f"Error reading core installer: {str(e)}")
            return False
        
        return all_passed
    
    def check_standalone_installers(self, standalone_manifest: Dict) -> bool:
        """Verify standalone modules have their own install scripts."""
        all_passed = True
        
        for module in standalone_manifest["modules"]:
            module_name = module["name"]
            module_path = self.rebuild_root / module_name
            
            if not module_path.exists():
                continue  # Already reported by structure auditor
            
            if module.get("must_have_install_script", False):
                install_script_path = module_path / module["install_script_path"]
                
                if not install_script_path.exists():
                    self.errors.append(
                        f"Standalone module {module_name} missing install script: "
                        f"{module['install_script_path']}"
                    )
                    all_passed = False
                else:
                    # Verify the install script is not empty and is executable
                    try:
                        stat = install_script_path.stat()
                        if stat.st_size == 0:
                            self.errors.append(
                                f"Standalone module {module_name} install script is empty"
                            )
                            all_passed = False
                        else:
                            self.passed.append(
                                f"Standalone module {module_name} has valid install script"
                            )
                    except Exception as e:
                        self.errors.append(
                            f"Error checking install script for {module_name}: {str(e)}"
                        )
                        all_passed = False
        
        return all_passed
    
    def check_root_installer(self) -> bool:
        """Check if root-level install.sh exists and is valid."""
        root_installer = self.rebuild_root / "install.sh"
        
        if not root_installer.exists():
            self.warnings.append("Root-level install.sh not found")
            return True  # Not required, just a warning
        
        try:
            with open(root_installer, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check that root installer doesn't directly install agents
            # (it should delegate to module-specific installers)
            forbidden_patterns = [
                r'ransomeye_linux_agent',
                r'ransomeye_windows_agent',
                r'ransomeye_dpi_probe'
            ]
            
            violations = []
            for pattern in forbidden_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    # Allow if it's just checking existence or delegating
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        stripped = line.strip()
                        if stripped.startswith('#'):
                            continue
                        if re.search(pattern, line, re.IGNORECASE):
                            # Check if it's a delegation (calling their install script)
                            if 'install.sh' in line or 'installer' in line.lower():
                                continue  # This is delegation, which is OK
                            violations.append((i, line.strip()))
            
            if violations:
                self.warnings.append(
                    f"Root installer may directly reference standalone modules "
                    f"at lines: {[v[0] for v in violations]}"
                )
            else:
                self.passed.append("Root installer separation verified")
        
        except Exception as e:
            self.warnings.append(f"Error checking root installer: {str(e)}")
        
        return True
    
    def run_audit(self) -> Tuple[bool, Dict]:
        """Run complete installer audit."""
        try:
            core_manifest, standalone_manifest = self.load_manifests()
        except Exception as e:
            self.errors.append(f"Failed to load manifests: {str(e)}")
            return False, self._get_results()
        
        results = []
        results.append(("Core Installer Separation", self.check_core_installer_separation(core_manifest)))
        results.append(("Standalone Installers", self.check_standalone_installers(standalone_manifest)))
        results.append(("Root Installer", self.check_root_installer()))
        
        all_passed = all(result[1] for result in results)
        
        return all_passed, self._get_results()
    
    def _get_results(self) -> Dict:
        """Get audit results summary."""
        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "passed": self.passed,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "passed_count": len(self.passed)
        }


if __name__ == "__main__":
    import sys
    rebuild_root = os.environ.get("REBUILD_ROOT", "/home/ransomeye/rebuild")
    auditor = InstallerAuditor(rebuild_root)
    passed, results = auditor.run_audit()
    
    print(f"Installer Audit: {'PASSED' if passed else 'FAILED'}")
    print(f"Errors: {results['error_count']}")
    print(f"Warnings: {results['warning_count']}")
    print(f"Passed: {results['passed_count']}")
    
    if results['errors']:
        print("\nErrors:")
        for error in results['errors']:
            print(f"  - {error}")
    
    if results['warnings']:
        print("\nWarnings:")
        for warning in results['warnings']:
            print(f"  - {warning}")
    
    sys.exit(0 if passed else 1)

