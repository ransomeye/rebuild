# Path and File Name : /home/ransomeye/rebuild/ransomeye_governance/audits/port_usage_audit.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Recursively scans codebase for hardcoded ports using regex patterns, fails on restricted ports outside whitelisted files

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Set
import fnmatch

# Project root
PROJECT_ROOT = Path("/home/ransomeye/rebuild")

# Restricted ports that must not be hardcoded
RESTRICTED_PORTS = {8080, 5432, 3000, 3306, 6379, 8443, 9090, 9091, 9092, 9093, 9094}

# Whitelisted file patterns (ports allowed in these files)
WHITELISTED_PATTERNS = [
    "**/.env",
    "**/.env.example",
    "**/config.yaml",
    "**/config.yml",
    "**/verification_policies.yaml",
    "**/requirements.txt",
    "**/README.md",
    "**/*.md",
    "**/port_usage_audit.py",  # This file itself
    "**/check_gates.py",
    "**/release_readiness.sh",
]

# Allowed contexts (ports in these contexts are OK)
ALLOWED_CONTEXTS = [
    r"os\.environ\.get\s*\([^)]*port",
    r"os\.getenv\s*\([^)]*port",
    r"config\.get\s*\([^)]*port",
    r"default.*port",
    r"PORT.*=.*os\.environ",
    r"port.*=.*os\.environ",
    r"#.*port",  # Comments
    r"//.*port",  # Comments
    r"/\*.*port.*\*/",  # Comments
    r"port.*#",  # Comments
    r"port.*//",  # Comments
]

# Exclude directories
EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    "logs",
    ".idea",
    ".vscode",
}

# File extensions to scan
SCAN_EXTENSIONS = {".py", ".js", ".ts", ".sh", ".yaml", ".yml", ".json"}

# Port patterns to detect
PORT_PATTERNS = [
    # Pattern: :PORT or :PORT/ or :PORT"
    r":(\d{2,5})(?:[/\"'`\s]|$)",
    # Pattern: port = PORT or port=PORT
    r"port\s*[=:]\s*(\d{2,5})(?:\s|,|;|\)|$)",
    # Pattern: PORT:PORT (like in URLs, but we'll check context)
    r"://[^:]+:(\d{2,5})(?:[/\s]|$)",
    # Pattern: 'PORT' or "PORT" as standalone number
    r"['\"](\d{2,5})['\"]",
    # Pattern: PORT, (in lists)
    r"(\d{2,5})\s*,",
    # Pattern: PORT) (in function calls)
    r"(\d{2,5})\s*\)",
]


class PortAuditor:
    """Scans codebase for hardcoded ports."""
    
    def __init__(self, project_root: Path = PROJECT_ROOT):
        self.project_root = project_root
        self.violations: List[Dict[str, any]] = []
        self.whitelisted_files: Set[Path] = set()
        self.scanned_files = 0
        self.total_matches = 0
    
    def is_whitelisted(self, file_path: Path) -> bool:
        """Check if file is whitelisted."""
        rel_path = file_path.relative_to(self.project_root)
        rel_str = str(rel_path)
        
        for pattern in WHITELISTED_PATTERNS:
            if fnmatch.fnmatch(rel_str, pattern) or fnmatch.fnmatch(str(file_path), pattern):
                return True
        return False
    
    def is_excluded_dir(self, path: Path) -> bool:
        """Check if directory should be excluded."""
        for part in path.parts:
            if part in EXCLUDE_DIRS:
                return True
        return False
    
    def is_allowed_context(self, line: str, port: str, match_start: int, match_end: int) -> bool:
        """Check if port match is in an allowed context."""
        # Get context around the match (50 chars before and after)
        context_start = max(0, match_start - 50)
        context_end = min(len(line), match_end + 50)
        context = line[context_start:context_end]
        
        # Check against allowed patterns
        for pattern in ALLOWED_CONTEXTS:
            if re.search(pattern, context, re.IGNORECASE):
                return True
        
        # Check if it's part of a version number (e.g., "1.2.3" should not match port 2)
        # Look for version-like patterns
        version_pattern = r'\d+\.\d+\.\d+'
        if re.search(version_pattern, context):
            # Check if our port is part of a version
            version_match = re.search(version_pattern, context)
            if version_match and port in version_match.group():
                return True
        
        return False
    
    def scan_file(self, file_path: Path) -> List[Dict[str, any]]:
        """Scan a single file for hardcoded ports."""
        violations = []
        
        if self.is_whitelisted(file_path):
            self.whitelisted_files.add(file_path)
            return violations
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            # Skip files that can't be read
            return violations
        
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            for pattern in PORT_PATTERNS:
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    port_str = match.group(1)
                    try:
                        port = int(port_str)
                    except ValueError:
                        continue
                    
                    # Skip if not a restricted port
                    if port not in RESTRICTED_PORTS:
                        continue
                    
                    # Check if in allowed context
                    if self.is_allowed_context(line, port_str, match.start(), match.end()):
                        continue
                    
                    # Found violation
                    rel_path = file_path.relative_to(self.project_root)
                    violation = {
                        "file": str(rel_path),
                        "line": line_num,
                        "port": port,
                        "context": line.strip()[:100],
                        "match": match.group(0)
                    }
                    violations.append(violation)
                    self.total_matches += 1
        
        return violations
    
    def scan_directory(self, directory: Path = None) -> None:
        """Recursively scan directory for hardcoded ports."""
        if directory is None:
            directory = self.project_root
        
        if self.is_excluded_dir(directory):
            return
        
        for item in directory.iterdir():
            if item.is_dir():
                if not self.is_excluded_dir(item):
                    self.scan_directory(item)
            elif item.is_file():
                if item.suffix in SCAN_EXTENSIONS:
                    self.scanned_files += 1
                    file_violations = self.scan_file(item)
                    self.violations.extend(file_violations)
    
    def generate_report(self) -> str:
        """Generate audit report."""
        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append("Port Usage Audit Report")
        report_lines.append("=" * 70)
        report_lines.append(f"Project Root: {self.project_root}")
        report_lines.append(f"Files Scanned: {self.scanned_files}")
        report_lines.append(f"Whitelisted Files: {len(self.whitelisted_files)}")
        report_lines.append(f"Total Violations: {len(self.violations)}")
        report_lines.append("")
        
        if self.violations:
            report_lines.append("❌ VIOLATIONS FOUND:")
            report_lines.append("")
            
            # Group by file
            violations_by_file: Dict[str, List[Dict]] = {}
            for violation in self.violations:
                file_path = violation["file"]
                if file_path not in violations_by_file:
                    violations_by_file[file_path] = []
                violations_by_file[file_path].append(violation)
            
            for file_path, file_violations in sorted(violations_by_file.items()):
                report_lines.append(f"File: {file_path}")
                for violation in file_violations:
                    report_lines.append(f"  Line {violation['line']}: Port {violation['port']} found")
                    report_lines.append(f"    Context: {violation['context']}")
                    report_lines.append(f"    Match: {violation['match']}")
                report_lines.append("")
        else:
            report_lines.append("✅ NO VIOLATIONS FOUND")
            report_lines.append("")
            report_lines.append("All restricted ports are either:")
            report_lines.append("  - In whitelisted configuration files")
            report_lines.append("  - In allowed context (environment variables, config.get, etc.)")
            report_lines.append("  - Not present in the codebase")
        
        report_lines.append("=" * 70)
        return "\n".join(report_lines)
    
    def run_audit(self) -> bool:
        """Run the complete audit."""
        print("Scanning codebase for hardcoded ports...")
        print(f"Restricted ports: {sorted(RESTRICTED_PORTS)}")
        print("")
        
        self.scan_directory()
        
        report = self.generate_report()
        print(report)
        
        return len(self.violations) == 0


def main():
    """Main entry point."""
    auditor = PortAuditor()
    success = auditor.run_audit()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

