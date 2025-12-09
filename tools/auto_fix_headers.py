# Path and File Name : /home/ransomeye/rebuild/tools/auto_fix_headers.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Automatically fixes missing file headers in .py and .sh files by prepending the required header block

import os
import re
from pathlib import Path
from typing import List


class HeaderFixer:
    """Automatically fixes missing file headers."""
    
    REQUIRED_AUTHOR = "nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU"
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
    ]
    
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.fixed_files: List[str] = []
        self.skipped_files: List[str] = []
        
    def should_process_file(self, file_path: Path) -> bool:
        """Determine if a file should be processed."""
        # Only process .py and .sh files
        if file_path.suffix not in ['.py', '.sh']:
            return False
        
        # Check exclusions
        file_str = str(file_path.relative_to(self.root_dir))
        for pattern in self.EXCLUDED_PATTERNS:
            if re.search(pattern, file_str, re.IGNORECASE):
                return False
        
        return True
    
    def has_header(self, file_path: Path) -> bool:
        """Check if file already has the required header."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Read first 10 lines to check for header
                lines = f.readlines()[:10]
                content = '\n'.join(lines)
                
                # Check if author string exists
                if self.REQUIRED_AUTHOR in content:
                    return True
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return False
        
        return False
    
    def generate_header(self, file_path: Path) -> str:
        """Generate the header block for a file."""
        absolute_path = str(file_path.resolve())
        header = f"""# Path and File Name : {absolute_path}
# Author: {self.REQUIRED_AUTHOR}
# Details of functionality of this file: Auto-generated header for compliance

"""
        return header
    
    def fix_file_header(self, file_path: Path) -> bool:
        """Fix missing header in a file."""
        if not self.should_process_file(file_path):
            return False
        
        if self.has_header(file_path):
            return False
        
        try:
            # Read existing content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                existing_content = f.read()
            
            # Generate header
            header = self.generate_header(file_path)
            
            # Prepend header to content
            new_content = header + existing_content
            
            # Write back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return True
        except Exception as e:
            print(f"Error fixing {file_path}: {e}")
            return False
    
    def scan_and_fix(self) -> None:
        """Recursively scan and fix all files."""
        print(f"Scanning {self.root_dir} for files missing headers...")
        print()
        
        for root, dirs, files in os.walk(self.root_dir):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not any(
                re.search(pattern, d, re.IGNORECASE) for pattern in self.EXCLUDED_PATTERNS
            )]
            
            for file_name in files:
                file_path = Path(root) / file_name
                
                if self.fix_file_header(file_path):
                    rel_path = file_path.relative_to(self.root_dir)
                    self.fixed_files.append(str(rel_path))
                    print(f"✓ Fixed: {rel_path}")
        
        print()
        print(f"Total files fixed: {len(self.fixed_files)}")
        
        if self.fixed_files:
            print("\nFixed files:")
            for file_path in self.fixed_files:
                print(f"  - {file_path}")


def main():
    """Main entry point."""
    import sys
    
    root_dir = os.environ.get('REBUILD_ROOT', '/home/ransomeye/rebuild')
    
    if len(sys.argv) > 1:
        root_dir = sys.argv[1]
    
    fixer = HeaderFixer(root_dir)
    fixer.scan_and_fix()


if __name__ == "__main__":
    main()

