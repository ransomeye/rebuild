# Path and File Name : /home/ransomeye/rebuild/ransomeye_delivery_assurance/tools/scan_for_forbidden.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Scans codebase for forbidden patterns: sample data files, hardcoded IPs, and credentials

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Set


class ForbiddenPatternScanner:
    """Scans codebase for forbidden patterns and security issues."""
    
    # Forbidden filename patterns
    FORBIDDEN_FILENAMES = [
        r'sample_data\.csv',
        r'sample.*\.csv',
        r'test\.pcap',
        r'sample.*\.pcap',
        r'dummy.*\.pkl',
        r'test.*\.pkl',
        r'placeholder.*\.json',
        r'sample.*\.json'
    ]
    
    # IPv4 regex (excluding localhost)
    IPV4_PATTERN = re.compile(
        r'\b(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
        r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
        r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
        r'(?:25[0-5]|2[0-9][0-9]|[01]?[0-9][0-9]?)\b'
    )
    
    # Allowed IPs (localhost variants)
    ALLOWED_IPS = {
        '127.0.0.1', 'localhost', '0.0.0.0', '::1',
        '127.0.0.1:8080', '127.0.0.1:5432', '127.0.0.1:8000'
    }
    
    # Common credential patterns
    CREDENTIAL_PATTERNS = [
        (r'password\s*=\s*["\']([^"\']+)["\']', 'Hardcoded password'),
        (r'passwd\s*=\s*["\']([^"\']+)["\']', 'Hardcoded password'),
        (r'pwd\s*=\s*["\']([^"\']+)["\']', 'Hardcoded password'),
        (r'api[_-]?key\s*=\s*["\']([^"\']{10,})["\']', 'Hardcoded API key'),
        (r'secret\s*=\s*["\']([^"\']{10,})["\']', 'Hardcoded secret'),
        (r'token\s*=\s*["\']([^"\']{10,})["\']', 'Hardcoded token'),
        (r'DB_PASS\s*=\s*["\']([^"\']+)["\']', 'Hardcoded DB password'),
        (r'password:\s*["\']([^"\']+)["\']', 'Hardcoded password in YAML/JSON'),
    ]
    
    EXCLUDED_PATTERNS = [
        r'__pycache__',
        r'\.pyc$',
        r'\.pyo$',
        r'\.egg-info',
        r'node_modules',
        r'\.git',
        r'venv',
        r'\.venv',
        r'\.pem$',
        r'\.key$',
        r'\.crt$',
        r'\.cert$',
        r'logs/',
        r'\.log$',
        r'\.md$',  # Documentation may contain examples
        r'tests/',  # Test files may contain sample data
        r'docs/',  # Documentation
        r'\.env\.example',
        r'sample\.env',
        r'definitions/',  # Manifest files
    ]
    
    def __init__(self, rebuild_root: str):
        self.rebuild_root = Path(rebuild_root)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed: List[str] = []
        self.files_scanned = 0
        
    def should_scan_file(self, file_path: Path) -> bool:
        """Determine if a file should be scanned."""
        file_str = str(file_path.relative_to(self.rebuild_root))
        
        # Check exclusions
        for pattern in self.EXCLUDED_PATTERNS:
            if re.search(pattern, file_str, re.IGNORECASE):
                return False
        
        return True
    
    def check_forbidden_filenames(self, file_path: Path) -> List[str]:
        """Check if filename matches forbidden patterns."""
        issues = []
        filename = file_path.name
        
        for pattern in self.FORBIDDEN_FILENAMES:
            if re.search(pattern, filename, re.IGNORECASE):
                issues.append(f"Forbidden filename pattern: {pattern}")
        
        return issues
    
    def check_hardcoded_ips(self, content: str, file_path: Path) -> List[str]:
        """Check for hardcoded IP addresses (excluding localhost)."""
        issues = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('//'):
                continue
            
            # Find all IP matches
            matches = self.IPV4_PATTERN.findall(line)
            for match in matches:
                # Reconstruct full IP
                ip_match = re.search(
                    r'\b' + re.escape(match) + r'\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
                    line
                )
                if ip_match:
                    full_ip = ip_match.group(0)
                    # Check if it's in allowed list
                    if full_ip not in self.ALLOWED_IPS and not any(
                        full_ip.startswith(allowed) for allowed in ['127.', '0.0.0.0', '::']
                    ):
                        # Additional check: is it a private IP that might be hardcoded?
                        if full_ip.startswith(('192.168.', '10.', '172.')):
                            issues.append(
                                f"Line {line_num}: Hardcoded private IP: {full_ip}"
                            )
                        elif not full_ip.startswith('127.'):
                            issues.append(
                                f"Line {line_num}: Potential hardcoded IP: {full_ip}"
                            )
        
        return issues
    
    def check_hardcoded_credentials(self, content: str, file_path: Path) -> List[str]:
        """Check for hardcoded credentials."""
        issues = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('//'):
                continue
            
            # Skip if it's clearly using environment variables
            if 'os.environ' in line or 'os.getenv' in line or '${' in line:
                continue
            
            # Check each credential pattern
            for pattern, description in self.CREDENTIAL_PATTERNS:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    value = match.group(1) if match.groups() else match.group(0)
                    # Skip if value is clearly a variable reference
                    if value.startswith(('$', '${', '%', 'os.environ', 'getenv')):
                        continue
                    # Skip if it's a placeholder
                    if value.lower() in ['password', 'secret', 'key', 'token', 'changeme', 'your_key']:
                        continue
                    issues.append(
                        f"Line {line_num}: {description} found: {value[:20]}..."
                    )
        
        return issues
    
    def scan_file(self, file_path: Path) -> Tuple[List[str], List[str]]:
        """Scan a single file for forbidden patterns."""
        errors = []
        warnings = []
        
        # Check filename
        filename_issues = self.check_forbidden_filenames(file_path)
        errors.extend(filename_issues)
        
        # Read file content for content-based checks
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Check for hardcoded IPs
            ip_issues = self.check_hardcoded_ips(content, file_path)
            errors.extend(ip_issues)
            
            # Check for hardcoded credentials
            cred_issues = self.check_hardcoded_credentials(content, file_path)
            errors.extend(cred_issues)
        
        except Exception as e:
            warnings.append(f"Error scanning file: {str(e)}")
        
        return errors, warnings
    
    def scan_directory(self, directory: Path) -> None:
        """Recursively scan directory for forbidden patterns."""
        if not directory.exists():
            return
        
        for root, dirs, files in os.walk(directory):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not any(
                re.search(pattern, d, re.IGNORECASE) for pattern in self.EXCLUDED_PATTERNS
            )]
            
            for file_name in files:
                file_path = Path(root) / file_name
                
                if not self.should_scan_file(file_path):
                    continue
                
                self.files_scanned += 1
                errors, warnings = self.scan_file(file_path)
                
                rel_path = file_path.relative_to(self.rebuild_root)
                
                if errors:
                    for error in errors:
                        self.errors.append(f"{rel_path}: {error}")
                if warnings:
                    for warning in warnings:
                        self.warnings.append(f"{rel_path}: {warning}")
                if not errors and not warnings:
                    self.passed.append(str(rel_path))
    
    def run_scan(self, target_modules: List[str] = None) -> Tuple[bool, Dict]:
        """Run forbidden pattern scan."""
        if target_modules:
            modules_to_scan = [self.rebuild_root / mod for mod in target_modules]
        else:
            # Scan all ransomeye_* directories
            modules_to_scan = [
                d for d in self.rebuild_root.iterdir()
                if d.is_dir() and d.name.startswith('ransomeye_')
            ]
        
        # Scan each module
        for module_dir in modules_to_scan:
            if module_dir.exists() and module_dir.is_dir():
                self.scan_directory(module_dir)
        
        all_passed = len(self.errors) == 0
        
        return all_passed, self._get_results()
    
    def _get_results(self) -> Dict:
        """Get scan results summary."""
        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "passed": self.passed,
            "files_scanned": self.files_scanned,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "passed_count": len(self.passed)
        }


if __name__ == "__main__":
    import sys
    rebuild_root = os.environ.get("REBUILD_ROOT", "/home/ransomeye/rebuild")
    scanner = ForbiddenPatternScanner(rebuild_root)
    passed, results = scanner.run_scan()
    
    print(f"Forbidden Pattern Scan: {'PASSED' if passed else 'FAILED'}")
    print(f"Files scanned: {results['files_scanned']}")
    print(f"Errors: {results['error_count']}")
    print(f"Warnings: {results['warning_count']}")
    print(f"Passed: {results['passed_count']}")
    
    if results['errors']:
        print("\nErrors (showing first 30):")
        for error in results['errors'][:30]:
            print(f"  - {error}")
        if len(results['errors']) > 30:
            print(f"  ... and {len(results['errors']) - 30} more")
    
    if results['warnings']:
        print("\nWarnings (showing first 10):")
        for warning in results['warnings'][:10]:
            print(f"  - {warning}")
        if len(results['warnings']) > 10:
            print(f"  ... and {len(results['warnings']) - 10} more")
    
    sys.exit(0 if passed else 1)

