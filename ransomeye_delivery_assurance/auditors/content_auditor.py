# Path and File Name : /home/ransomeye/rebuild/ransomeye_delivery_assurance/auditors/content_auditor.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Verifies file headers exist in the first 5 lines of every .py/.sh file

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple


class ContentAuditor:
    """Audits file content for required headers."""
    
    REQUIRED_HEADER_PATTERNS = [
        r"# Path and File Name\s*:",
        r"# Author:\s*nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU",
        r"# Details of functionality of this file:"
    ]
    
    EXCLUDED_PATTERNS = [
        r"__pycache__",
        r"\.pyc$",
        r"\.pyo$",
        r"\.egg-info",
        r"node_modules",
        r"\.git",
        r"venv",
        r"\.venv",
        r"tests/.*test_.*\.py",  # Test files may have different headers
        r"docs/.*\.md"  # Markdown files don't need Python headers
    ]
    
    def __init__(self, rebuild_root: str):
        self.rebuild_root = Path(rebuild_root)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed: List[str] = []
        self.files_checked = 0
        
    def should_check_file(self, file_path: Path) -> bool:
        """Determine if a file should be checked for headers."""
        # Only check .py and .sh files
        if file_path.suffix not in ['.py', '.sh']:
            return False
        
        # Check exclusions
        file_str = str(file_path.relative_to(self.rebuild_root))
        for pattern in self.EXCLUDED_PATTERNS:
            if re.search(pattern, file_str, re.IGNORECASE):
                return False
        
        return True
    
    def check_file_header(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Check if file has required header in first 5 lines."""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = [line.rstrip() for line in f.readlines()[:5]]
            
            if not lines:
                issues.append("File is empty")
                return False, issues
            
            # Check for each required pattern
            content = '\n'.join(lines)
            for pattern in self.REQUIRED_HEADER_PATTERNS:
                if not re.search(pattern, content, re.IGNORECASE):
                    issues.append(f"Missing pattern: {pattern}")
            
            # Verify author is exact match
            author_found = False
            for line in lines:
                if "Author:" in line and "nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU" in line:
                    author_found = True
                    break
            
            if not author_found:
                issues.append("Author field missing or incorrect")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            issues.append(f"Error reading file: {str(e)}")
            return False, issues
    
    def audit_directory(self, directory: Path) -> None:
        """Recursively audit all files in directory."""
        if not directory.exists():
            return
        
        for root, dirs, files in os.walk(directory):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not any(
                re.search(pattern, d, re.IGNORECASE) for pattern in self.EXCLUDED_PATTERNS
            )]
            
            for file_name in files:
                file_path = Path(root) / file_name
                
                if not self.should_check_file(file_path):
                    continue
                
                self.files_checked += 1
                passed, issues = self.check_file_header(file_path)
                
                rel_path = file_path.relative_to(self.rebuild_root)
                
                if passed:
                    self.passed.append(str(rel_path))
                else:
                    self.errors.append(f"{rel_path}: {', '.join(issues)}")
    
    def run_audit(self, target_modules: List[str] = None) -> Tuple[bool, Dict]:
        """Run content audit on specified modules or all modules."""
        if target_modules:
            modules_to_check = [self.rebuild_root / mod for mod in target_modules]
        else:
            # Check all ransomeye_* directories
            modules_to_check = [
                d for d in self.rebuild_root.iterdir()
                if d.is_dir() and d.name.startswith('ransomeye_')
            ]
        
        # Also check root-level scripts
        root_scripts = [
            self.rebuild_root / "install.sh",
            self.rebuild_root / "uninstall.sh"
        ]
        
        for script in root_scripts:
            if script.exists() and self.should_check_file(script):
                self.files_checked += 1
                passed, issues = self.check_file_header(script)
                if passed:
                    self.passed.append(script.name)
                else:
                    self.errors.append(f"{script.name}: {', '.join(issues)}")
        
        # Audit each module
        for module_dir in modules_to_check:
            if module_dir.exists() and module_dir.is_dir():
                self.audit_directory(module_dir)
        
        all_passed = len(self.errors) == 0
        
        return all_passed, self._get_results()
    
    def _get_results(self) -> Dict:
        """Get audit results summary."""
        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "passed": self.passed,
            "files_checked": self.files_checked,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "passed_count": len(self.passed)
        }


if __name__ == "__main__":
    import sys
    rebuild_root = os.environ.get("REBUILD_ROOT", "/home/ransomeye/rebuild")
    auditor = ContentAuditor(rebuild_root)
    passed, results = auditor.run_audit()
    
    print(f"Content Audit: {'PASSED' if passed else 'FAILED'}")
    print(f"Files checked: {results['files_checked']}")
    print(f"Errors: {results['error_count']}")
    print(f"Passed: {results['passed_count']}")
    
    if results['errors']:
        print("\nErrors (showing first 20):")
        for error in results['errors'][:20]:
            print(f"  - {error}")
        if len(results['errors']) > 20:
            print(f"  ... and {len(results['errors']) - 20} more")
    
    sys.exit(0 if passed else 1)

