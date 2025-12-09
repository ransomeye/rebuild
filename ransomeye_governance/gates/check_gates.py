# Path and File Name : /home/ransomeye/rebuild/ransomeye_governance/gates/check_gates.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Automated acceptance gate verification for mTLS, SHAP, Buffer, and Signing requirements

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import json

# Project root
PROJECT_ROOT = Path("/home/ransomeye/rebuild")

# Required file patterns per module
REQUIRED_PATTERNS = {
    "mtls": {
        "linux_agent": {
            "path": "ransomeye_linux_agent/transport/agent_client.py",
            "patterns": [
                r"AGENT_CERT_PATH",
                r"AGENT_KEY_PATH",
                r"cert.*=.*\(.*cert_path.*key_path",
                r"verify.*=.*True",
                r"ssl.*context|SSLContext"
            ]
        },
        "windows_agent": {
            "path": "ransomeye_windows_agent/transport/agent_client.py",
            "patterns": [
                r"AGENT_CERT_PATH",
                r"AGENT_KEY_PATH",
                r"cert.*=.*\(.*cert_path.*key_path",
                r"verify.*=.*True",
                r"ssl.*context|SSLContext"
            ]
        },
        "dpi_probe": {
            "path": "ransomeye_dpi_probe/transport/probe_client.py",
            "patterns": [
                r"PROBE_CERT_PATH",
                r"cert.*=.*\(.*cert_path.*key_path",
                r"verify.*=.*True"
            ]
        }
    },
    "shap": {
        "ai_core": {
            "path": "ransomeye_ai_core",
            "file_pattern": "**/shap*.py",
            "required": True
        },
        "forensic": {
            "path": "ransomeye_forensic",
            "file_pattern": "**/shap*.py",
            "required": True
        },
        "hnmp_engine": {
            "path": "ransomeye_hnmp_engine",
            "file_pattern": "**/shap*.py",
            "required": True
        },
        "dpi_probe": {
            "path": "ransomeye_dpi_probe",
            "file_pattern": "**/shap*.py",
            "required": True
        },
        "linux_agent": {
            "path": "ransomeye_linux_agent",
            "file_pattern": "**/shap*.py",
            "required": True
        },
        "windows_agent": {
            "path": "ransomeye_windows_agent",
            "file_pattern": "**/shap*.py",
            "required": True
        }
    },
    "buffer": {
        "linux_agent": {
            "path": "ransomeye_linux_agent/engine/persistence.py",
            "patterns": [
                r"BUFFER_DIR",
                r"buffer",
                r"persist|Persistence"
            ]
        },
        "windows_agent": {
            "path": "ransomeye_windows_agent/engine/persistence.py",
            "patterns": [
                r"BUFFER_DIR",
                r"buffer",
                r"persist|Persistence"
            ]
        },
        "dpi_probe": {
            "path": "ransomeye_dpi_probe",
            "file_pattern": "**/persistence.py",
            "required": False  # May be in transport or engine
        }
    },
    "signing": {
        "linux_agent": {
            "path": "ransomeye_linux_agent/updater/apply_update.sh",
            "required": True
        },
        "windows_agent": {
            "path": "ransomeye_windows_agent/updater/apply_update.ps1",
            "required": True
        }
    }
}


class GateChecker:
    """Automated gate verification for RansomEye requirements."""
    
    def __init__(self, project_root: Path = PROJECT_ROOT):
        self.project_root = project_root
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed: List[str] = []
    
    def check_mtls(self) -> bool:
        """Verify mTLS implementation in agents and probe."""
        print("\n[GATE] Checking mTLS Implementation...")
        all_passed = True
        
        for module_name, config in REQUIRED_PATTERNS["mtls"].items():
            file_path = self.project_root / config["path"]
            
            if not file_path.exists():
                error_msg = f"❌ mTLS: {module_name} - File not found: {file_path}"
                self.errors.append(error_msg)
                print(error_msg)
                all_passed = False
                continue
            
            # Read file content
            try:
                content = file_path.read_text(encoding='utf-8')
            except Exception as e:
                error_msg = f"❌ mTLS: {module_name} - Cannot read file: {e}"
                self.errors.append(error_msg)
                print(error_msg)
                all_passed = False
                continue
            
            # Check for required patterns
            found_patterns = []
            for pattern in config["patterns"]:
                if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                    found_patterns.append(pattern)
            
            if len(found_patterns) >= 2:  # At least 2 patterns must match
                success_msg = f"✅ mTLS: {module_name} - Verified ({len(found_patterns)}/{len(config['patterns'])} patterns)"
                self.passed.append(success_msg)
                print(success_msg)
            else:
                error_msg = f"❌ mTLS: {module_name} - Insufficient patterns found ({len(found_patterns)}/{len(config['patterns'])})"
                self.errors.append(error_msg)
                print(error_msg)
                all_passed = False
        
        return all_passed
    
    def check_shap(self) -> bool:
        """Verify SHAP explainability files exist in ML modules."""
        print("\n[GATE] Checking SHAP Explainability...")
        all_passed = True
        
        for module_name, config in REQUIRED_PATTERNS["shap"].items():
            module_path = self.project_root / config["path"]
            
            if not module_path.exists():
                error_msg = f"❌ SHAP: {module_name} - Module path not found: {module_path}"
                self.errors.append(error_msg)
                print(error_msg)
                all_passed = False
                continue
            
            # Search for SHAP files
            shap_files = list(module_path.rglob(config["file_pattern"]))
            
            if shap_files:
                success_msg = f"✅ SHAP: {module_name} - Found {len(shap_files)} file(s): {[f.name for f in shap_files]}"
                self.passed.append(success_msg)
                print(success_msg)
            elif config.get("required", True):
                error_msg = f"❌ SHAP: {module_name} - No SHAP files found (required)"
                self.errors.append(error_msg)
                print(error_msg)
                all_passed = False
            else:
                warning_msg = f"⚠️  SHAP: {module_name} - No SHAP files found (optional)"
                self.warnings.append(warning_msg)
                print(warning_msg)
        
        return all_passed
    
    def check_buffer(self) -> bool:
        """Verify buffer/persistence logic in agents and probe."""
        print("\n[GATE] Checking Buffer/Persistence...")
        all_passed = True
        
        for module_name, config in REQUIRED_PATTERNS["buffer"].items():
            if "file_pattern" in config:
                # Search pattern
                module_path = self.project_root / config["path"]
                if not module_path.exists():
                    if config.get("required", True):
                        error_msg = f"❌ Buffer: {module_name} - Module path not found: {module_path}"
                        self.errors.append(error_msg)
                        print(error_msg)
                        all_passed = False
                    continue
                
                persistence_files = list(module_path.rglob(config["file_pattern"]))
                if persistence_files:
                    success_msg = f"✅ Buffer: {module_name} - Found persistence file(s): {[f.name for f in persistence_files]}"
                    self.passed.append(success_msg)
                    print(success_msg)
                elif config.get("required", True):
                    error_msg = f"❌ Buffer: {module_name} - No persistence file found (required)"
                    self.errors.append(error_msg)
                    print(error_msg)
                    all_passed = False
            else:
                # Specific file path
                file_path = self.project_root / config["path"]
                
                if not file_path.exists():
                    error_msg = f"❌ Buffer: {module_name} - File not found: {file_path}"
                    self.errors.append(error_msg)
                    print(error_msg)
                    all_passed = False
                    continue
                
                # Check for required patterns
                try:
                    content = file_path.read_text(encoding='utf-8')
                except Exception as e:
                    error_msg = f"❌ Buffer: {module_name} - Cannot read file: {e}"
                    self.errors.append(error_msg)
                    print(error_msg)
                    all_passed = False
                    continue
                
                found_patterns = []
                for pattern in config["patterns"]:
                    if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                        found_patterns.append(pattern)
                
                if len(found_patterns) >= 2:
                    success_msg = f"✅ Buffer: {module_name} - Verified ({len(found_patterns)}/{len(config['patterns'])} patterns)"
                    self.passed.append(success_msg)
                    print(success_msg)
                else:
                    error_msg = f"❌ Buffer: {module_name} - Insufficient patterns found ({len(found_patterns)}/{len(config['patterns'])})"
                    self.errors.append(error_msg)
                    print(error_msg)
                    all_passed = False
        
        return all_passed
    
    def check_signing(self) -> bool:
        """Verify signed update scripts exist."""
        print("\n[GATE] Checking Signed Updates...")
        all_passed = True
        
        for module_name, config in REQUIRED_PATTERNS["signing"].items():
            file_path = self.project_root / config["path"]
            
            if not file_path.exists():
                error_msg = f"❌ Signing: {module_name} - Update script not found: {file_path}"
                self.errors.append(error_msg)
                print(error_msg)
                all_passed = False
                continue
            
            # Check if file has content (not empty)
            try:
                content = file_path.read_text(encoding='utf-8')
                if len(content.strip()) < 10:
                    error_msg = f"❌ Signing: {module_name} - Update script appears empty or placeholder"
                    self.errors.append(error_msg)
                    print(error_msg)
                    all_passed = False
                    continue
                
                # Check for signature verification patterns
                has_signature_check = False
                if file_path.suffix == '.sh':
                    # Shell script - look for signature verification
                    if re.search(r'signature|verify|gpg|openssl.*verify', content, re.IGNORECASE):
                        has_signature_check = True
                elif file_path.suffix == '.ps1':
                    # PowerShell script - look for signature verification
                    if re.search(r'Signature|Verify|Get-AuthenticodeSignature', content, re.IGNORECASE):
                        has_signature_check = True
                
                if has_signature_check:
                    success_msg = f"✅ Signing: {module_name} - Update script found with signature verification"
                    self.passed.append(success_msg)
                    print(success_msg)
                else:
                    warning_msg = f"⚠️  Signing: {module_name} - Update script found but signature verification not detected"
                    self.warnings.append(warning_msg)
                    print(warning_msg)
            except Exception as e:
                error_msg = f"❌ Signing: {module_name} - Cannot read file: {e}"
                self.errors.append(error_msg)
                print(error_msg)
                all_passed = False
        
        return all_passed
    
    def run_all_checks(self) -> bool:
        """Run all gate checks."""
        print("=" * 70)
        print("RansomEye Acceptance Gate Verification")
        print("=" * 70)
        
        results = {
            "mtls": self.check_mtls(),
            "shap": self.check_shap(),
            "buffer": self.check_buffer(),
            "signing": self.check_signing()
        }
        
        # Print summary
        print("\n" + "=" * 70)
        print("GATE VERIFICATION SUMMARY")
        print("=" * 70)
        
        for check_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{check_name.upper()}: {status}")
        
        print(f"\nPassed: {len(self.passed)}")
        print(f"Warnings: {len(self.warnings)}")
        print(f"Errors: {len(self.errors)}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(f"  - {error}")
        
        all_passed = all(results.values())
        
        if all_passed:
            print("\n✅ ALL GATES PASSED")
        else:
            print("\n❌ ONE OR MORE GATES FAILED")
        
        return all_passed


def main():
    """Main entry point."""
    checker = GateChecker()
    success = checker.run_all_checks()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

