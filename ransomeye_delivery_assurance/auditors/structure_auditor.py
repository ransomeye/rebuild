# Path and File Name : /home/ransomeye/rebuild/ransomeye_delivery_assurance/auditors/structure_auditor.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Verifies folder existence, separation of concerns, and required directory structure

import os
import json
from pathlib import Path
from typing import Dict, List, Tuple


class StructureAuditor:
    """Audits directory structure and module organization."""
    
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
    
    def verify_core_modules(self, core_manifest: Dict) -> bool:
        """Verify all core modules exist."""
        all_passed = True
        
        for module in core_manifest["modules"]:
            module_name = module["name"]
            module_path = self.rebuild_root / module_name
            
            if not module_path.exists():
                self.errors.append(f"Core module missing: {module_name}")
                all_passed = False
            elif not module_path.is_dir():
                self.errors.append(f"Core module is not a directory: {module_name}")
                all_passed = False
            else:
                self.passed.append(f"Core module exists: {module_name}")
                
                # Check for required subdirectories
                tests_dir = module_path / "tests"
                if not tests_dir.exists():
                    self.warnings.append(f"Module {module_name} missing tests/ directory")
                
                docs_dir = module_path / "docs"
                readme_path = module_path / "README.md"
                if not readme_path.exists() and not (docs_dir.exists() and (docs_dir / "README.md").exists()):
                    self.warnings.append(f"Module {module_name} missing README.md")
        
        return all_passed
    
    def verify_standalone_modules(self, standalone_manifest: Dict) -> bool:
        """Verify standalone modules exist and have install scripts."""
        all_passed = True
        
        for module in standalone_manifest["modules"]:
            module_name = module["name"]
            module_path = self.rebuild_root / module_name
            
            if not module_path.exists():
                self.errors.append(f"Standalone module missing: {module_name}")
                all_passed = False
                continue
                
            if not module_path.is_dir():
                self.errors.append(f"Standalone module is not a directory: {module_name}")
                all_passed = False
                continue
            
            self.passed.append(f"Standalone module exists: {module_name}")
            
            # Check for install script
            if module.get("must_have_install_script", False):
                install_script_path = module_path / module["install_script_path"]
                if not install_script_path.exists():
                    self.errors.append(
                        f"Standalone module {module_name} missing install script: {install_script_path}"
                    )
                    all_passed = False
                else:
                    self.passed.append(f"Standalone module {module_name} has install script")
        
        return all_passed
    
    def verify_required_directories(self, core_manifest: Dict) -> bool:
        """Verify required root-level directories exist."""
        all_passed = True
        
        for dir_name in core_manifest.get("required_directories", []):
            dir_path = self.rebuild_root / dir_name
            if not dir_path.exists():
                self.errors.append(f"Required directory missing: {dir_name}")
                all_passed = False
            elif not dir_path.is_dir():
                self.errors.append(f"Required path is not a directory: {dir_name}")
                all_passed = False
            else:
                self.passed.append(f"Required directory exists: {dir_name}")
        
        return all_passed
    
    def verify_separation(self, core_manifest: Dict) -> bool:
        """Verify core modules are separate from standalone modules."""
        all_passed = True
        core_module_names = {m["name"] for m in core_manifest["modules"]}
        
        # Check that standalone modules are not in core
        standalone_dir = self.rebuild_root / "ransomeye_linux_agent"
        if standalone_dir.exists() and "ransomeye_linux_agent" in core_module_names:
            self.errors.append("Standalone module ransomeye_linux_agent should not be in core manifest")
            all_passed = False
        
        return all_passed
    
    def run_audit(self) -> Tuple[bool, Dict]:
        """Run complete structure audit."""
        try:
            core_manifest, standalone_manifest = self.load_manifests()
        except Exception as e:
            self.errors.append(f"Failed to load manifests: {str(e)}")
            return False, self._get_results()
        
        results = []
        results.append(("Core Modules", self.verify_core_modules(core_manifest)))
        results.append(("Standalone Modules", self.verify_standalone_modules(standalone_manifest)))
        results.append(("Required Directories", self.verify_required_directories(core_manifest)))
        results.append(("Separation", self.verify_separation(core_manifest)))
        
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
    auditor = StructureAuditor(rebuild_root)
    passed, results = auditor.run_audit()
    
    print(f"Structure Audit: {'PASSED' if passed else 'FAILED'}")
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

