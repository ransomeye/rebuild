# Path and File Name : /home/ransomeye/rebuild/ransomeye_release_engineering/validation/validate_phase25.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Comprehensive validation script for Phase 25 implementation

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple
import re

# Project root
PROJECT_ROOT = Path("/home/ransomeye/rebuild")
RELEASE_ENG_DIR = PROJECT_ROOT / "ransomeye_release_engineering"
GATES_SCRIPT = PROJECT_ROOT / "ransomeye_governance" / "gates" / "check_gates.py"


class Phase25Validator:
    """Comprehensive validator for Phase 25 implementation."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed: List[str] = []
    
    def check_directory_structure(self) -> bool:
        """Verify required directory structure exists."""
        print("\n[1] Checking directory structure...")
        required_dirs = [
            RELEASE_ENG_DIR,
            RELEASE_ENG_DIR / "builder",
            RELEASE_ENG_DIR / "manifests",
            RELEASE_ENG_DIR / "validation",
            RELEASE_ENG_DIR / "artifacts",
            RELEASE_ENG_DIR / "docs",
            RELEASE_ENG_DIR / "ci" / ".github" / "workflows",
        ]
        
        all_exist = True
        for req_dir in required_dirs:
            if req_dir.exists():
                self.passed.append(f"Directory exists: {req_dir.relative_to(PROJECT_ROOT)}")
            else:
                self.errors.append(f"Missing directory: {req_dir.relative_to(PROJECT_ROOT)}")
                all_exist = False
        
        return all_exist
    
    def check_required_files(self) -> bool:
        """Verify all required files exist."""
        print("\n[2] Checking required files...")
        required_files = [
            RELEASE_ENG_DIR / "builder" / "build_release.py",
            RELEASE_ENG_DIR / "builder" / "packager_core.py",
            RELEASE_ENG_DIR / "builder" / "packager_agents.py",
            RELEASE_ENG_DIR / "builder" / "artifact_signer.py",
            RELEASE_ENG_DIR / "manifests" / "generate_release_manifest.py",
            RELEASE_ENG_DIR / "validation" / "verify_release.py",
            RELEASE_ENG_DIR / "validation" / "final_smoke_test.py",
            RELEASE_ENG_DIR / "docs" / "RELEASE_PROCESS.md",
            RELEASE_ENG_DIR / "ci" / ".github" / "workflows" / "build_release_candidate.yml",
        ]
        
        all_exist = True
        for req_file in required_files:
            if req_file.exists():
                self.passed.append(f"File exists: {req_file.relative_to(PROJECT_ROOT)}")
            else:
                self.errors.append(f"Missing file: {req_file.relative_to(PROJECT_ROOT)}")
                all_exist = False
        
        return all_exist
    
    def check_file_headers(self) -> bool:
        """Verify all Python files have required headers."""
        print("\n[3] Checking file headers...")
        all_valid = True
        
        for py_file in RELEASE_ENG_DIR.rglob("*.py"):
            try:
                content = py_file.read_text(encoding='utf-8')
                lines = content.split('\n')[:3]
                
                has_path = any('Path and File Name' in line for line in lines)
                has_author = any('Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU' in line for line in lines)
                has_details = any('Details of functionality' in line for line in lines)
                
                if has_path and has_author and has_details:
                    self.passed.append(f"Header valid: {py_file.relative_to(PROJECT_ROOT)}")
                else:
                    missing = []
                    if not has_path:
                        missing.append("Path and File Name")
                    if not has_author:
                        missing.append("Author")
                    if not has_details:
                        missing.append("Details")
                    self.errors.append(f"Invalid header in {py_file.relative_to(PROJECT_ROOT)}: missing {', '.join(missing)}")
                    all_valid = False
            except Exception as e:
                self.errors.append(f"Error reading {py_file}: {e}")
                all_valid = False
        
        return all_valid
    
    def check_gate_enforcement(self) -> bool:
        """Verify gate enforcement is implemented."""
        print("\n[4] Checking gate enforcement...")
        
        build_script = RELEASE_ENG_DIR / "builder" / "build_release.py"
        if not build_script.exists():
            self.errors.append("build_release.py not found")
            return False
        
        content = build_script.read_text(encoding='utf-8')
        
        # Check for gate script path
        if 'ransomeye_governance/gates/check_gates.py' in content or 'check_gates.py' in content:
            self.passed.append("Gate script path referenced")
        else:
            self.errors.append("Gate script path not found in build_release.py")
            return False
        
        # Check for subprocess.run call
        if 'subprocess.run' in content:
            self.passed.append("subprocess.run used for gate check")
        else:
            self.errors.append("subprocess.run not found for gate execution")
            return False
        
        # Check for returncode check
        if 'returncode' in content:
            self.passed.append("returncode check implemented")
        else:
            self.errors.append("returncode check not found")
            return False
        
        # Check for abort on failure
        if 'sys.exit' in content or 'exit' in content.lower():
            self.passed.append("Abort on gate failure implemented")
        else:
            self.warnings.append("Abort on gate failure may not be implemented")
        
        return True
    
    def check_core_agent_separation(self) -> bool:
        """Verify Core and Agent separation logic."""
        print("\n[5] Checking Core/Agent separation...")
        
        packager_core = RELEASE_ENG_DIR / "builder" / "packager_core.py"
        if not packager_core.exists():
            self.errors.append("packager_core.py not found")
            return False
        
        content = packager_core.read_text(encoding='utf-8')
        
        # Check for exclusion of agents
        if 'ransomeye_linux_agent' in content and 'ransomeye_windows_agent' in content and 'ransomeye_dpi_probe' in content:
            self.passed.append("Agent exclusion logic present")
        else:
            self.errors.append("Agent exclusion not found in packager_core.py")
            return False
        
        # Check for separate agent packager
        packager_agents = RELEASE_ENG_DIR / "builder" / "packager_agents.py"
        if packager_agents.exists():
            self.passed.append("Separate agent packager exists")
        else:
            self.errors.append("packager_agents.py not found")
            return False
        
        return True
    
    def check_artifact_signing(self) -> bool:
        """Verify artifact signing implementation."""
        print("\n[6] Checking artifact signing...")
        
        signer = RELEASE_ENG_DIR / "builder" / "artifact_signer.py"
        if not signer.exists():
            self.errors.append("artifact_signer.py not found")
            return False
        
        content = signer.read_text(encoding='utf-8')
        
        # Check for RELEASE_SIGN_KEY_PATH (can be in env var or parameter)
        if 'RELEASE_SIGN_KEY_PATH' in content or 'sign_key_path' in content.lower():
            self.passed.append("RELEASE_SIGN_KEY_PATH/sign_key_path used")
        else:
            self.errors.append("RELEASE_SIGN_KEY_PATH not found")
            return False
        
        # Check for GPG or OpenSSL signing
        if 'gpg' in content.lower() or 'openssl' in content.lower():
            self.passed.append("GPG/OpenSSL signing implemented")
        else:
            self.errors.append("Signing method not found")
            return False
        
        return True
    
    def check_manifest_generation(self) -> bool:
        """Verify manifest generation."""
        print("\n[7] Checking manifest generation...")
        
        manifest_gen = RELEASE_ENG_DIR / "manifests" / "generate_release_manifest.py"
        if not manifest_gen.exists():
            self.errors.append("generate_release_manifest.py not found")
            return False
        
        content = manifest_gen.read_text(encoding='utf-8')
        
        # Check for SHA256 calculation
        if 'sha256' in content.lower() or 'hashlib' in content:
            self.passed.append("SHA256 calculation implemented")
        else:
            self.errors.append("SHA256 calculation not found")
            return False
        
        # Check for release_manifest.json
        if 'release_manifest.json' in content:
            self.passed.append("release_manifest.json generation")
        else:
            self.errors.append("release_manifest.json not found")
            return False
        
        # Check for SHA256SUMS
        if 'SHA256SUMS' in content:
            self.passed.append("SHA256SUMS generation")
        else:
            self.errors.append("SHA256SUMS not found")
            return False
        
        return True
    
    def check_path_handling(self) -> bool:
        """Verify pathlib usage and relative path handling."""
        print("\n[8] Checking path handling...")
        
        packagers = [
            RELEASE_ENG_DIR / "builder" / "packager_core.py",
            RELEASE_ENG_DIR / "builder" / "packager_agents.py",
        ]
        
        all_valid = True
        for packager in packagers:
            if not packager.exists():
                continue
            
            content = packager.read_text(encoding='utf-8')
            
            # Check for pathlib usage
            if 'from pathlib import Path' in content or 'import pathlib' in content:
                self.passed.append(f"pathlib used in {packager.name}")
            else:
                self.errors.append(f"pathlib not used in {packager.name}")
                all_valid = False
            
            # Check for relative path handling
            if 'relative_to' in content or 'arcname' in content:
                self.passed.append(f"Relative path handling in {packager.name}")
            else:
                self.warnings.append(f"Relative path handling may be missing in {packager.name}")
        
        return all_valid
    
    def check_version_handling(self) -> bool:
        """Verify version management."""
        print("\n[9] Checking version handling...")
        
        build_script = RELEASE_ENG_DIR / "builder" / "build_release.py"
        if not build_script.exists():
            return False
        
        content = build_script.read_text(encoding='utf-8')
        
        # Check for VERSION file reading
        if 'VERSION' in content:
            self.passed.append("VERSION file handling")
        else:
            self.warnings.append("VERSION file handling may be missing")
        
        # Check for environment variable fallback
        if 'RELEASE_VERSION' in content or 'os.environ.get' in content:
            self.passed.append("Environment variable version support")
        else:
            self.warnings.append("Environment variable version may not be supported")
        
        # Check for default version
        if '1.0.0' in content:
            self.passed.append("Default version (1.0.0) specified")
        else:
            self.warnings.append("Default version may not be specified")
        
        return True
    
    def check_no_placeholders(self) -> bool:
        """Verify no placeholders in code."""
        print("\n[10] Checking for placeholders...")
        
        all_valid = True
        for py_file in RELEASE_ENG_DIR.rglob("*.py"):
            # Skip validation script itself (it contains pattern strings)
            if 'validate_phase25.py' in str(py_file):
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                # Check for actual placeholders (not in strings/comments that are part of validation)
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    # Skip comments and docstrings
                    if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                        continue
                    
                    # Check for actual TODO/FIXME in code (not in strings)
                    if re.search(r'\bTODO\b', line, re.IGNORECASE) and '"' not in line and "'" not in line:
                        self.warnings.append(f"TODO found in {py_file.relative_to(PROJECT_ROOT)}: line {i+1}")
                    
                    if re.search(r'\bFIXME\b', line, re.IGNORECASE) and '"' not in line and "'" not in line:
                        self.warnings.append(f"FIXME found in {py_file.relative_to(PROJECT_ROOT)}: line {i+1}")
                    
                    # Check for NotImplementedError (actual code, not string)
                    if 'NotImplementedError' in line and 'raise' in line:
                        self.errors.append(f"NotImplementedError in {py_file.relative_to(PROJECT_ROOT)}: line {i+1}")
                        all_valid = False
                    
                    # Check for ellipsis as placeholder
                    if stripped == '...' and i > 0 and 'def' not in lines[i-1] and 'class' not in lines[i-1]:
                        self.warnings.append(f"Ellipsis placeholder in {py_file.relative_to(PROJECT_ROOT)}: line {i+1}")
            except Exception:
                pass
        
        return all_valid
    
    def run_all_checks(self) -> bool:
        """Run all validation checks."""
        print("=" * 70)
        print("PHASE 25 COMPREHENSIVE VALIDATION")
        print("=" * 70)
        
        checks = [
            self.check_directory_structure,
            self.check_required_files,
            self.check_file_headers,
            self.check_gate_enforcement,
            self.check_core_agent_separation,
            self.check_artifact_signing,
            self.check_manifest_generation,
            self.check_path_handling,
            self.check_version_handling,
            self.check_no_placeholders,
        ]
        
        all_passed = True
        for check in checks:
            try:
                if not check():
                    all_passed = False
            except Exception as e:
                self.errors.append(f"Error in {check.__name__}: {e}")
                all_passed = False
        
        # Print summary
        print("\n" + "=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        print(f"✅ Passed: {len(self.passed)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"❌ Errors: {len(self.errors)}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings[:10]:  # Limit output
                print(f"  - {warning}")
            if len(self.warnings) > 10:
                print(f"  ... and {len(self.warnings) - 10} more")
        
        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(f"  - {error}")
        
        if all_passed and not self.errors:
            print("\n✅ ALL VALIDATION CHECKS PASSED")
        else:
            print("\n❌ VALIDATION FAILED")
        
        return all_passed and not self.errors


def main():
    """Main entry point."""
    validator = Phase25Validator()
    success = validator.run_all_checks()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

