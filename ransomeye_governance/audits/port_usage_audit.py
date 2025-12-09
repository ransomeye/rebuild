# Path and File Name : /home/ransomeye/rebuild/ransomeye_governance/audits/port_usage_audit.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Recursively scans codebase for hardcoded ports using regex patterns, fails on restricted ports outside whitelisted files

import os
import re
import sys
import json
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional
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
    "**/*.yaml",  # All YAML files (configs, datasources, etc.)
    "**/*.yml",
    "**/verification_policies.yaml",
    "**/requirements.txt",
    "**/README.md",
    "**/*.md",
    "**/port_usage_audit.py",  # This file itself
    "**/check_gates.py",
    "**/release_readiness.sh",
    "**/.github/workflows/*.yml",  # CI/CD workflows
    "**/.github/workflows/*.yaml",
    "**/install*.sh",  # Install scripts
    "**/preflight*.sh",  # Preflight checks
    "**/training_data/**/*.json",  # Training data files
    "**/vite.config.ts",  # Build configs
    "**/vite.config.js",
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
    "ci",  # CI directory may contain test configs
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
    
    def is_decimal_number(self, line: str, port_str: str, match_start: int) -> bool:
        """Check if port is part of a decimal number (false positive)."""
        # Check if there's a dot before or after the port
        before_char = line[match_start - 1] if match_start > 0 else ''
        after_char = line[match_start + len(port_str)] if match_start + len(port_str) < len(line) else ''
        
        # Check for decimal pattern like 0.5792243930103306
        decimal_pattern = r'\d+\.\d+' + re.escape(port_str)
        if re.search(decimal_pattern, line):
            return True
        
        # Check if surrounded by digits (part of larger number)
        if before_char.isdigit() or after_char.isdigit():
            # Check wider context
            context_start = max(0, match_start - 10)
            context_end = min(len(line), match_start + len(port_str) + 10)
            context = line[context_start:context_end]
            if re.search(r'\d+\.\d+', context):
                return True
        
        return False
    
    def is_in_comment(self, line: str, match_start: int) -> bool:
        """Check if match is in a comment."""
        line_before_match = line[:match_start]
        
        # Python/Shell comments
        if '#' in line_before_match:
            return True
        
        # JavaScript/TypeScript comments
        if '//' in line_before_match:
            return True
        
        # Multi-line comments (check if we're inside /* ... */)
        comment_start = line_before_match.rfind('/*')
        comment_end = line_before_match.rfind('*/')
        if comment_start > comment_end:
            return True
        
        # Check for docstring patterns
        if '"""' in line_before_match or "'''" in line_before_match:
            # Count quotes to see if we're inside a docstring
            triple_quotes = line_before_match.count('"""') + line_before_match.count("'''")
            if triple_quotes % 2 == 1:
                return True
        
        return False
    
    def is_default_value(self, line: str, port_str: str, match_start: int, match_end: int) -> bool:
        """Check if port is in a default value (os.environ.get, function defaults, etc.)."""
        # Get wider context
        context_start = max(0, match_start - 150)
        context_end = min(len(line), match_end + 150)
        context = line[context_start:context_end]
        full_line = line
        
        # Check for os.environ.get with default value (numeric or string)
        # Pattern: os.environ.get('KEY', 5432) or os.environ.get('KEY', '5432')
        env_get_patterns = [
            r'os\.environ\.get\s*\([^)]*,\s*' + re.escape(port_str) + r'(?:\s|,|\)|$)',
            r'os\.environ\.get\s*\([^)]*,\s*[\'"]' + re.escape(port_str) + r'[\'"]',
        ]
        for pattern in env_get_patterns:
            if re.search(pattern, context, re.IGNORECASE):
                return True
        
        # Check for os.getenv with default
        env_get_patterns = [
            r'os\.getenv\s*\([^)]*,\s*' + re.escape(port_str) + r'(?:\s|,|\)|$)',
            r'os\.getenv\s*\([^)]*,\s*[\'"]' + re.escape(port_str) + r'[\'"]',
        ]
        for pattern in env_get_patterns:
            if re.search(pattern, context, re.IGNORECASE):
                return True
        
        # Check for function default parameter: def func(port: int = 9092) or def func(port = 9092)
        if re.search(r'def\s+\w+\s*\([^)]*=\s*' + re.escape(port_str) + r'(?:\s|,|\)|$)', full_line, re.IGNORECASE):
            return True
        
        # Check for argparse default: default=9092
        if re.search(r'default\s*=\s*' + re.escape(port_str) + r'(?:\s|,|\)|$)', context, re.IGNORECASE):
            return True
        
        # Check for variable assignment with default in os.environ.get context
        # Pattern: port = int(os.environ.get('PORT', 8080))
        if re.search(r'=\s*int\s*\(\s*os\.environ\.get\s*\([^)]*,\s*' + re.escape(port_str), context, re.IGNORECASE):
            return True
        
        # Check for URL defaults in os.environ.get
        # Pattern: os.environ.get('URL', 'https://localhost:8443')
        if re.search(r'os\.environ\.get\s*\([^)]*,\s*[\'"]https?://[^:]+:' + re.escape(port_str), context, re.IGNORECASE):
            return True
        
        return False
    
    def is_legitimate_port_list(self, line: str, port_str: str) -> bool:
        """Check if port is in a legitimate list of common ports (for scanning, etc.)."""
        # Check if line contains multiple ports (likely a port list)
        port_count = len(re.findall(r'\b\d{2,5}\b', line))
        if port_count >= 5:  # Likely a port list
            # Check if it's in a variable assignment for scanning
            if re.search(r'(ports|common_ports|port_list)\s*=', line, re.IGNORECASE):
                return True
            # Check if it's in a list literal
            if '[' in line and ']' in line and port_count >= 5:
                return True
        
        return False
    
    def is_example_or_docstring(self, line: str) -> bool:
        """Check if line is an example or in a docstring."""
        line_lower = line.lower().strip()
        
        # Common example patterns
        example_patterns = [
            r'example:',
            r'e\.g\.',
            r'for example',
            r'sample:',
            r'optional.*url',
            r'redis://',
            r'postgres://',
            r'defaults? to',
            r'default:',
            r'\(default',
            r'help=.*port',
        ]
        
        for pattern in example_patterns:
            if re.search(pattern, line_lower):
                return True
        
        # Check if line is a docstring line (starts with quotes or has docstring markers)
        if line.strip().startswith('"""') or line.strip().startswith("'''"):
            return True
        
        # Check if it's a parameter description in docstring
        if re.search(r':\s*(Port|port).*\(', line_lower):
            return True
        
        return False
    
    def is_allowed_context(self, line: str, port_str: str, match_start: int, match_end: int) -> bool:
        """Check if port match is in an allowed context."""
        # Check if in comment
        if self.is_in_comment(line, match_start):
            return True
        
        # Check if part of decimal number
        if self.is_decimal_number(line, port_str, match_start):
            return True
        
        # Check if default value
        if self.is_default_value(line, port_str, match_start, match_end):
            return True
        
        # Check if legitimate port list
        if self.is_legitimate_port_list(line, port_str):
            return True
        
        # Check if example/docstring
        if self.is_example_or_docstring(line):
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
